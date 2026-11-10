# Jam original-file access (draft)

Target on media server: `/var/www/media/public_html/uploads/jam/.htaccess`.
This is a proposed Apache 2.4 rule, not a deployed change. It requires Apache
to honor `.htaccess` and `AllowOverride AuthConfig` (or `All`) for this path.

The rule allows the existing `FuzikAppAnimation.mp4` fallback asset to remain
public. The other hard-coded `/uploads/jam/Omie_06102022135409.mp4` references
in `Collab_*` components are currently inside comments. If any of those
examples become active, change them to use an allowed route before deployment.

No frontend changes are needed for the active fallback animation under this
rule.

After enabling it, verify a known original `/uploads/jam/<name>.mp4` returns
403, `FuzikAppAnimation.mp4` remains available, a normal
`/stream/jam_stream.php?code=...` still plays, and a paid Jam
download still succeeds. A 200 for the direct URL means the rule was not
applied; a 500 means inspect the Apache error log and override permissions.
The PHP built-in server ignores `.htaccess`, so its local 200 response is not
a valid test of this rule.
