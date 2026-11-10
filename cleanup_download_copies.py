"""Report and optionally remove abandoned temporary Jam download copies.

The PHP download endpoint normally removes each copy on shutdown. This script
handles copies left when the PHP worker is killed before its shutdown handler.
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

MIN_AGE = timedelta(hours=48)
MARKER = ".fuzik-download-copies"


def cleanup(directory: Path, apply: bool, now: datetime) -> None:
    directory = directory.resolve(strict=True)
    if not (directory / MARKER).is_file():
        raise ValueError(f"Missing {MARKER} marker in {directory}")
    count = 0
    for path in sorted(directory.iterdir()):
        if path.name == MARKER or not path.name.startswith("jam_"):
            continue
        if path.is_symlink() or not path.is_file() or path.resolve().parent != directory:
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if now - modified < MIN_AGE:
            continue
        print(f"{'DELETE' if apply else 'WOULD DELETE'} {path.name}")
        if apply:
            path.unlink()
        count += 1
    print(f"Eligible: {count}; dry_run: {not apply}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Delete eligible copies")
    args = parser.parse_args()
    cleanup(args.directory, args.apply, datetime.now(timezone.utc))


if __name__ == "__main__":
    main()
