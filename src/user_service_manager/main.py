"""Application entry point."""

from __future__ import annotations

import sys
import gettext
import locale
import os


def configure_locale() -> None:
    locale.setlocale(locale.LC_ALL, "")
    locale_dir = os.environ.get("USM_LOCALE_DIR")
    gettext.bindtextdomain("user-service-manager", locale_dir)
    gettext.textdomain("user-service-manager")


def main() -> int:
    configure_locale()
    from user_service_manager.presentation.application import UserServiceManagerApplication

    return UserServiceManagerApplication().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
