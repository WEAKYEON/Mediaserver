# Fuzik Media Server work

Internship implementation by Tanat Kunharee. This repository contains the media cleanup and protected Jam download changes prepared for review. It does not include the existing company media-server snapshot or video files.

## Files

- `cleanup_media.py`: manifest-driven move of approved void media to private Trash, with dry run by default; purge Trash after three days.
- `export_cleanup_manifest.py`: export active and void references from the Django database.
- `cleanup_download_copies.py`: remove abandoned temporary download copies.
- `stream/secure_jam_download.php`: verify a short-lived RSA-signed request, copy a Jam video to a private temporary file, stream the copy, then remove it.
- `secure_jam_download_smoke.py`: disposable authorization and copy test for the PHP endpoint.
- `apache/uploads_jam/.htaccess`: draft Apache rule blocking direct Jam MP4 URLs.
- `MEDIA_CLEANUP_RUNBOOK.md`, `MEDIA_SIGNED_DOWNLOAD.md`, and `APACHE_JAM_ACCESS.md`: review and deployment notes.

The PHP file belongs at `/var/www/media/public_html/stream/secure_jam_download.php` on the media server. The Apache rule belongs at `/var/www/media/public_html/uploads/jam/.htaccess` after its server configuration is checked. Backend authorization and the 30-day Transfer record are separate work in FuzikApp10.

These files have passed local syntax and disposable-file checks. They have not been deployed to the company media server. Do not run cleanup with `--apply` until the real database manifest and media paths have been reviewed.

The signed PHP endpoint uses a public RSA key on the Media Server; it does not use `MEDIA_DOWNLOAD_KEY`. The matching private key stays on the web server. Existing Jam playback still streams the original through the legacy route, so the paid-download change alone is not a complete original-file paywall.
