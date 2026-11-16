# Jam download handoff (local draft)

`FuzikFront3b-master29-integrated` checks the Django 30-day entitlement and
signs a 60-second, video-specific request for `secure_jam_download.php`.
PHP verifies the signature with a public RSA key before reading the original,
copies the file outside `public_html`, streams the copy, and deletes it.
`MEDIA_DOWNLOAD_KEY` and `X-Media-Download-Key` are no longer used by this PHP
endpoint. The separate Nuxt-to-Django `JAM_DOWNLOAD_API_KEY` still exists.

This is a source draft, not a live deployment. Keep
`NUXT_PUBLIC_JAM_DOWNLOAD_DEBIT_ENABLED`,
`NUXT_PUBLIC_JAM_DOWNLOAD_ENTITLEMENT_ENABLED`, and
`NUXT_MEDIA_SECURE_DOWNLOAD_ENABLED` off until the backend, media endpoint,
accounts, and server configuration have been reviewed together.

Production setup requires an RSA key pair of at least 2048 bits. Store the
private key only on the Nuxt server, base64-encoded in the server-only
`NUXT_MEDIA_DOWNLOAD_PRIVATE_KEY_BASE64` environment variable. Store only the
matching public PEM on the PHP server outside `public_html` and set
`MEDIA_DOWNLOAD_PUBLIC_KEY_FILE` to its absolute path. Enable PHP OpenSSL.
Also create a writable `MEDIA_DOWNLOAD_COPY_DIR` outside `public_html`.
Do not commit the private key, public key, or copied video files to a repo.

This paid-download change does not require editing or transcoding video.
The existing `jam_stream.php` remains unchanged and still streams the original
video through its legacy encoded URL. The Apache rule in
`APACHE_JAM_ACCESS.md` can block direct `/uploads/jam/` URLs, but it does not
close that legacy streaming route. Consequently, the original is not fully
protected until playback uses an already available restricted/preview source
or the playback design is changed separately. Do not represent the paid
download endpoint alone as a complete original-file paywall.
