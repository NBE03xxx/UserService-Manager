from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
import unittest

from user_service_manager.adapters.systemd_journal import SystemdJournalReader
from user_service_manager.application.journal_service import JournalService
from user_service_manager.domain.journal import JournalPage
from user_service_manager.domain.models import (
    AccessMode,
    ActiveState,
    LoadState,
    RegistrationState,
    UnitId,
    UnitRecord,
)


UNIT = UnitId("coffee.service")


class FakeReader:
    def __init__(self, entries: list[dict[str, object]]) -> None:
        self.entries = list(entries)
        self.matches: list[dict[str, object] | str] = []
        self.cursor: str | None = None

    def add_match(self, **values: object) -> None:
        self.matches.append(values)

    def add_disjunction(self) -> None:
        self.matches.append("OR")

    def seek_tail(self) -> None:
        pass

    def seek_cursor(self, cursor: str) -> None:
        self.cursor = cursor

    def get_previous(self):
        return self.entries.pop(0) if self.entries else None


def raw(cursor: str, message: object = "message", priority: object = 6):
    return {
        "__CURSOR": cursor,
        "__REALTIME_TIMESTAMP": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "PRIORITY": priority,
        "MESSAGE": message,
    }


class JournalAdapterTests(unittest.TestCase):
    def test_query_is_limited_by_uid_and_both_user_unit_fields(self) -> None:
        fake = FakeReader([raw("c1")])
        page = SystemdJournalReader(lambda: fake)._read_sync(UNIT, 10, None)
        self.assertEqual(
            fake.matches,
            [
                {"_UID": os.getuid(), "_SYSTEMD_USER_UNIT": UNIT.value},
                "OR",
                {"_UID": os.getuid(), "USER_UNIT": UNIT.value},
            ],
        )
        self.assertEqual(len(page.entries), 1)

    def test_limit_has_more_and_cursor(self) -> None:
        fake = FakeReader([raw("c3"), raw("c2"), raw("c1")])
        page = SystemdJournalReader(lambda: fake)._read_sync(UNIT, 2, None)
        self.assertEqual([entry.cursor for entry in page.entries], ["c3", "c2"])
        self.assertTrue(page.has_more)
        self.assertEqual(page.older_cursor, "c2")

    def test_before_cursor_is_not_repeated(self) -> None:
        fake = FakeReader([raw("c2"), raw("c1")])
        page = SystemdJournalReader(lambda: fake)._read_sync(UNIT, 10, "c2")
        self.assertEqual(fake.cursor, "c2")
        self.assertEqual([entry.cursor for entry in page.entries], ["c1"])

    def test_binary_and_large_messages_are_bounded(self) -> None:
        adapter = SystemdJournalReader(
            lambda: FakeReader([raw("c1", b"x" * 9_000, "invalid")])
        )
        entry = adapter._read_sync(UNIT, adapter.MAX_LIMIT, None).entries[0]
        self.assertTrue(entry.truncated)
        self.assertLessEqual(len(entry.message), adapter.MAX_MESSAGE_CHARS + 1)
        self.assertEqual(entry.priority, 6)


class FakeDiscovery:
    def __init__(self, present: bool) -> None:
        self.present = present

    async def scan(self):
        if not self.present:
            return ()
        return (
            UnitRecord(
                UNIT,
                "Coffee",
                LoadState.LOADED,
                ActiveState.ACTIVE,
                "running",
                "enabled",
                "/home/demo/coffee.service",
                AccessMode.READ_ONLY,
                RegistrationState.DISCOVERED,
            ),
        )


class FakeJournal:
    def __init__(self) -> None:
        self.calls = []

    async def read(self, unit_id, limit, before_cursor=None):
        self.calls.append((unit_id, limit, before_cursor))
        return JournalPage((), None, False)


class JournalServiceTests(unittest.TestCase):
    def test_read_only_discovered_unit_can_show_logs(self) -> None:
        journal = FakeJournal()
        result = asyncio.run(JournalService(FakeDiscovery(True), journal).read(UNIT))
        self.assertEqual(result, JournalPage((), None, False))
        self.assertEqual(journal.calls, [(UNIT, 100, None)])

    def test_undiscovered_unit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            asyncio.run(JournalService(FakeDiscovery(False), FakeJournal()).read(UNIT))


if __name__ == "__main__":
    unittest.main()
