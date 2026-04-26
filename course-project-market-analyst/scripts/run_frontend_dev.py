from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"


def main() -> int:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if not (FRONTEND_DIR / "package.json").exists():
        print(f"Frontend package.json not found: {FRONTEND_DIR / 'package.json'}", file=sys.stderr)
        return 1

    print(f"Starting Vite dev server from: {FRONTEND_DIR}", flush=True)
    return subprocess.call([npm, "run", "dev"], cwd=FRONTEND_DIR)


if __name__ == "__main__":
    raise SystemExit(main())

