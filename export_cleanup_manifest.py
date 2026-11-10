"""Export a reviewable media cleanup manifest from the Django database.

Run from the Django project environment with DJANGO_SETTINGS_MODULE set.
The output is JSON; redirect it to a protected file and transfer that file to
the media server. No database records are changed.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import urlsplit

ALLOWED_PREFIXES = ("uploads/videos/", "uploads/jam/")
JAM_FILENAME = re.compile(r"^[A-Za-z0-9._-]+\.(?:mp4|png|jpg|jpeg|webp)$", re.IGNORECASE)


def media_path(value):
    if not isinstance(value, str) or not value:
        return None
    if value.startswith("https://"):
        parsed = urlsplit(value)
        if parsed.netloc != "media05.fuzikapp.com" or parsed.query or parsed.fragment:
            return None
        value = parsed.path.lstrip("/")
    if "\\" in value or ".." in PurePosixPath(value).parts:
        return None
    if not value.startswith(ALLOWED_PREFIXES):
        return None
    if PurePosixPath(value).suffix.lower() not in {".mp4", ".png", ".jpg", ".jpeg", ".webp"}:
        return None
    return value


def jam_media_path(value):
    path = media_path(value)
    if path:
        return path
    if isinstance(value, str) and JAM_FILENAME.fullmatch(value):
        return "uploads/jam/" + value
    return None


def locations(record, fields, parser=media_path):
    paths = set()
    for field in fields:
        value = getattr(record, field, None)
        if value in (None, "", "None"):
            continue
        path = parser(value)
        if path is None:
            raise ValueError(f"Unrecognized media location in {type(record).__name__}.{field}: {value!r}")
        paths.add(path)
    return paths


def play_locations(record):
    paths = locations(record, ("video_location", "preview"))
    video = media_path(record.video_location)
    if video and video.endswith(".mp4"):
        paths.add(video[:-4] + "_120.mp4")
    return paths


def build_manifest():
    from musicapp.models import Jam2, PlayVideo2

    protected = set()
    void_files = set()
    plays = 0
    jams = 0
    for record in PlayVideo2.objects.all().iterator():
        plays += 1
        (void_files if record.void == "1" else protected).update(play_locations(record))
    for record in Jam2.objects.all().iterator():
        jams += 1
        own = locations(record, ("file_location", "preview"), jam_media_path)
        if record.void == "1":
            void_files.update(own)
        else:
            protected.update(own)
            protected.update(locations(record, (
                "video01_location", "video02_location", "video03_location", "video04_location"
            )))
    if plays == 0 and jams == 0:
        raise RuntimeError("No media records found; refusing to export an empty database snapshot")
    return {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": {"play2": plays, "jam2": jams},
        "void_files": sorted(void_files - protected),
        "protected_files": sorted(protected),
    }


def main():
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        raise SystemExit("Set DJANGO_SETTINGS_MODULE before running this script")
    import django
    django.setup()
    json.dump(build_manifest(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
