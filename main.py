# new-agent/main.py
"""CLI entry point for the intelligent study companion."""

import sys
import io


def _fix_windows_encoding():
    """Force UTF-8 on Windows to avoid GBK encoding crashes with Rich spinner characters."""
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


_fix_windows_encoding()

from cli.interface import CLI  # noqa: E402


def main():
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
