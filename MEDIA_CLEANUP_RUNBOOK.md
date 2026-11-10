# Media cleanup: first deployment review

This is a staged procedure. Nothing below schedules a job or changes live files.
Run the exporter in the **Django backend environment** and the cleanup script
on the **server that owns `/var/www/media/public_html/uploads`**. The Ubuntu
video-editing server may be a different machine.

## 1. Export and inspect the database manifest

Use the backend's real `DJANGO_SETTINGS_MODULE` and Python environment. Run
`export_cleanup_manifest.py` from a location where `musicapp.models` imports.
Store output in a private directory, never under `public_html`.

```bash
export DJANGO_SETTINGS_MODULE='<deployed Django settings module>'
python3 export_cleanup_manifest.py > /private/cleanup-manifest.json
python3 -m json.tool /private/cleanup-manifest.json >/dev/null
```

Review `record_counts`, `void_files`, and `protected_files`. Export stops on an
unrecognized nonempty media location. Resolve those values before continuing.
The manifest is accepted only for 24 hours after `generated_at`.

## 2. Review on the media file server (no changes)

Verify the actual media root and a private Trash directory. Trash must be
outside `public_html` and must contain `.fuzik-media-trash` as a marker. Copy
the fresh manifest securely from the backend server. Do not use a guessed or
empty manifest.

```bash
python3 cleanup_media.py \
  --root /var/www/media/public_html \
  --trash /var/www/media/trash \
  --manifest /private/cleanup-manifest.json

python3 cleanup_media.py \
  --root /var/www/media/public_html \
  --manifest /private/cleanup-manifest.json \
  --report-orphans

python3 cleanup_media.py --root /var/www/media/public_html \
  --trash /var/www/media/trash --purge
```

Expected: `WOULD MOVE` only for approved void files older than three days;
`POSSIBLE ORPHAN` is report-only; `WOULD DELETE` only for files already in Trash
for at least three days. Check representative paths against the database and
confirm currently playable videos remain protected.

## 3. Later, after review

Only after checking the dry-run output, use `--apply` for the approved move
and purge jobs. Set schedules on the server that owns the media files. Before
scheduling, verify the job's account has access, logs go to a private location,
and a new manifest is generated for each run. A stale or missing manifest must
stop the move job.

The local `media_cleanup_smoke.py` and `secure_jam_download_smoke.py` are
developer checks and do not need to be deployed.
