# Fuzik Media Server work

## Files

- `cleanup_media.py`: manifest-driven move of approved void media to private Trash, with dry run by default; purge Trash after three days.
- `export_cleanup_manifest.py`: export active and void references from the Django database.
- `cleanup_download_copies.py`: remove abandoned temporary download copies.
- `stream/secure_jam_download.php`: copy a Jam video to a private temporary file, stream the copy, then remove it.
- `apache/uploads_jam/.htaccess`: draft Apache rule blocking direct Jam MP4 URLs.
- `MEDIA_CLEANUP_RUNBOOK.md` and `APACHE_JAM_ACCESS.md`: review and deployment notes.

The PHP file belongs at `/var/www/media/public_html/stream/secure_jam_download.php` on the media server. The Apache rule belongs at `/var/www/media/public_html/uploads/jam/.htaccess` after its server configuration is checked. Backend authorization and the 30-day Transfer record are separate work in FuzikApp10.

These files have passed local syntax and disposable-file checks. They have not been deployed to the company media server. Do not run cleanup with `--apply` until the real database manifest and media paths have been reviewed.
