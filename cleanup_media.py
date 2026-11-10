"""Review and optionally move approved, unreferenced media files to Trash.

The database server must generate the JSON manifest. This script never infers
that a file is unused from its timestamp alone.
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

ALLOWED_DIRS = {"videos", "jam"}
ALLOWED_EXTENSIONS = {".mp4", ".png", ".jpg", ".jpeg", ".webp"}
MAX_MANIFEST_AGE = timedelta(hours=24)
MIN_SOURCE_AGE = timedelta(days=3)
TRASH_RETENTION = timedelta(days=3)
MIN_ORPHAN_AGE = timedelta(days=7)


def safe_relative_path(raw: str) -> Path:
    if not isinstance(raw, str):
        raise ValueError("Manifest path must be text")
    if "\\" in raw:
        raise ValueError(f"Unsafe media path: {raw!r}")
    parts = PurePosixPath(raw).parts
    if len(parts) < 3 or parts[0] != "uploads" or parts[1] not in ALLOWED_DIRS:
        raise ValueError(f"Unsupported media path: {raw!r}")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe media path: {raw!r}")
    if PurePosixPath(raw).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported extension: {raw!r}")
    return Path(*parts)


def within(path: Path, directory: Path) -> bool:
    return path.resolve().is_relative_to(directory.resolve())


def check_trash_marker(trash: Path) -> None:
    if not (trash / ".fuzik-media-trash").is_file():
        raise ValueError("Trash marker .fuzik-media-trash is missing")


def load_manifest(path: Path, now: datetime) -> tuple[set[Path], set[Path]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("Unsupported manifest schema")
    generated = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    if generated.tzinfo is None or not timedelta(0) <= now - generated <= MAX_MANIFEST_AGE:
        raise ValueError("Manifest is stale or has an invalid timestamp")
    candidates = {safe_relative_path(value) for value in data["void_files"]}
    protected = {safe_relative_path(value) for value in data["protected_files"]}
    return candidates, protected


def review_and_move(root: Path, trash: Path, manifest: Path, apply: bool, now: datetime) -> None:
    root = root.resolve(strict=True)
    trash = trash.resolve(strict=True)
    check_trash_marker(trash)
    if trash.is_relative_to(root) or root.is_relative_to(trash):
        raise ValueError("Trash and public media directories must be separate")
    candidates, protected = load_manifest(manifest, now)
    moved = 0
    for relative in sorted(candidates):
        if relative in protected:
            print(f"PROTECTED {relative.as_posix()}")
            continue
        source = root / relative
        if source.is_symlink() or not source.is_file() or not within(source, root):
            print(f"SKIP missing or unsafe {relative.as_posix()}")
            continue
        if now - datetime.fromtimestamp(source.stat().st_mtime, timezone.utc) < MIN_SOURCE_AGE:
            print(f"SKIP recent {relative.as_posix()}")
            continue
        destination = trash / now.strftime("%Y-%m-%d") / relative
        if not within(destination.parent, trash) or destination.exists():
            print(f"SKIP destination exists or unsafe {relative.as_posix()}")
            continue
        print(f"{'MOVE' if apply else 'WOULD MOVE'} {relative.as_posix()}")
        if apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            os.utime(destination, (now.timestamp(), now.timestamp()))
            moved += 1
    print(f"Candidates: {len(candidates)}; moved: {moved}; dry_run: {not apply}")


def review_and_purge(trash: Path, apply: bool, now: datetime) -> None:
    trash = trash.resolve(strict=True)
    check_trash_marker(trash)
    removed = 0
    for path in sorted(trash.rglob("*")):
        if path == trash / ".fuzik-media-trash":
            continue
        if path.is_symlink() or not path.is_file() or not within(path, trash):
            continue
        if now - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < TRASH_RETENTION:
            continue
        print(f"{'DELETE' if apply else 'WOULD DELETE'} {path.relative_to(trash)}")
        if apply:
            path.unlink()
            removed += 1
    print(f"Deleted: {removed}; dry_run: {not apply}")


def report_possible_orphans(root: Path, manifest: Path, now: datetime) -> None:
    """Report old files absent from this manifest; never move or delete them."""
    root = root.resolve(strict=True)
    candidates, protected = load_manifest(manifest, now)
    referenced = candidates | protected
    found = 0
    for directory in (root / "uploads" / "videos", root / "uploads" / "jam"):
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_symlink() or not path.is_file() or not within(path, root):
                continue
            relative = path.relative_to(root)
            try:
                relative = safe_relative_path(relative.as_posix())
            except ValueError:
                continue
            if relative in referenced:
                continue
            if now - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < MIN_ORPHAN_AGE:
                continue
            print(f"POSSIBLE ORPHAN {relative.as_posix()}")
            found += 1
    print(f"Possible orphans: {found}; report only")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Media public_html root")
    parser.add_argument("--trash", type=Path, help="Private Trash directory")
    parser.add_argument("--manifest", type=Path, help="Fresh JSON manifest from backend")
    parser.add_argument("--purge", action="store_true", help="Purge old Trash files instead of moving")
    parser.add_argument("--report-orphans", action="store_true", help="Report old files absent from the manifest; never delete")
    parser.add_argument("--apply", action="store_true", help="Perform the reported changes")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.report_orphans:
        if args.apply or args.purge or not args.manifest:
            parser.error("--report-orphans requires --manifest and cannot use --apply or --purge")
        report_possible_orphans(args.root, args.manifest, now)
    elif args.purge:
        if not args.trash:
            parser.error("--trash is required for --purge")
        review_and_purge(args.trash, args.apply, now)
    elif args.manifest:
        if not args.trash:
            parser.error("--trash is required to move files")
        review_and_move(args.root, args.trash, args.manifest, args.apply, now)
    else:
        parser.error("--manifest is required unless --purge is selected")


if __name__ == "__main__":
    main()
