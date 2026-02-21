#!/usr/bin/env python3
from __future__ import annotations

import os
import sys


def main() -> int:
    prompt = sys.argv[1] if len(sys.argv) > 1 else ""
    token = (
        os.environ.get("GIT_UPDATE_ACCESS_TOKEN")
        or os.environ.get("GIT_ACCESS_TOKEN")
        or ""
    )
    username = os.environ.get("GIT_UPDATE_GIT_USERNAME") or "x-access-token"

    if "Username" in prompt:
        sys.stdout.write(username + "\n")
        sys.stdout.flush()
        return 0

    # Git sometimes asks "Password", sometimes it just asks for credentials.
    sys.stdout.write(token + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
