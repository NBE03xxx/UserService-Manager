"""Typed preference values independent of GSettings storage."""

from __future__ import annotations

from enum import StrEnum


class AppearancePreference(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"

    @classmethod
    def parse(cls, value: str) -> "AppearancePreference":
        try:
            return cls(value)
        except ValueError:
            return cls.SYSTEM


class LanguagePreference(StrEnum):
    SYSTEM = "system"
    JAPANESE = "ja"
    ENGLISH = "en"
