#!/usr/bin/env python3
"""Compile the project's simple gettext PO catalog without external msgfmt."""

from __future__ import annotations

import ast
from pathlib import Path
import struct
import sys


def read_catalog(path: Path) -> dict[str, str]:
    messages: dict[str, str] = {}
    msgid: list[str] = []
    msgstr: list[str] = []
    active: list[str] | None = None

    def commit() -> None:
        nonlocal msgid, msgstr, active
        if msgid or msgstr:
            messages["".join(msgid)] = "".join(msgstr)
        msgid = []
        msgstr = []
        active = None

    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if not line.strip():
            commit()
        elif line.startswith("msgid "):
            msgid = [ast.literal_eval(line[6:])]
            active = msgid
        elif line.startswith("msgstr "):
            msgstr = [ast.literal_eval(line[7:])]
            active = msgstr
        elif line.startswith('"') and active is not None:
            active.append(ast.literal_eval(line))
    return messages


def compile_catalog(messages: dict[str, str]) -> bytes:
    keys = sorted(messages)
    ids = [key.encode("utf-8") for key in keys]
    values = [messages[key].encode("utf-8") for key in keys]
    count = len(keys)
    header_size = 7 * 4
    original_table = header_size
    translation_table = original_table + count * 8
    original_data = translation_table + count * 8
    ids_blob = b"\0".join(ids) + b"\0"
    translation_data = original_data + len(ids_blob)
    values_blob = b"\0".join(values) + b"\0"

    output = bytearray(
        struct.pack(
            "<7I",
            0x950412DE,
            0,
            count,
            original_table,
            translation_table,
            0,
            0,
        )
    )
    offset = original_data
    for value in ids:
        output.extend(struct.pack("<2I", len(value), offset))
        offset += len(value) + 1
    offset = translation_data
    for value in values:
        output.extend(struct.pack("<2I", len(value), offset))
        offset += len(value) + 1
    output.extend(ids_blob)
    output.extend(values_blob)
    return bytes(output)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: compile_mo.py INPUT.po OUTPUT.mo", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(compile_catalog(read_catalog(source)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
