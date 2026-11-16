"""Disposable local check of signed PHP Jam downloads (never touches live files)."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization

PHP = Path(sys.argv[1] if len(sys.argv) > 1 else
           shutil.which("php") or r"D:\Coded\php\php.exe")
SOURCE = Path(sys.argv[2] if len(sys.argv) > 2 else
              Path(__file__).parent / "stream" / "secure_jam_download.php")
if not PHP.is_file() or not SOURCE.is_file():
    raise SystemExit("Pass the PHP executable and secure_jam_download.php paths")
plain = "MUbzFknEOsjG7HaKgYov.62d9VlRZfpyWcq_1D0PS3QT45LNiIAmCBx8teJrhX-uw"
coded = "sY6ndv30.jHQVNBmEo5eLXKSGcFZ8R1bpDAa_iMlTuw9t2IUxgqO4kzrC7JyhWP-f"
filename = "smoke-video.mp4"
code = "".join(coded[plain.index(c)] for c in filename)
content = b"disposable video fixture"
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def url64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def ticket(method, *, expires=None, signed_code=code):
    payload = url64(json.dumps({"v": 1, "code": signed_code, "method": method,
                                "exp": expires or int(time.time()) + 60}, separators=(",", ":")).encode())
    signature = private_key.sign(payload.encode(), padding.PKCS1v15(), hashes.SHA256())
    return payload + "." + url64(signature)


with tempfile.TemporaryDirectory(prefix="fuzik-signed-download-") as temp:
    base = Path(temp)
    public = base / "public_html"
    stream = public / "stream"
    jam = public / "uploads" / "jam"
    copies = base / "download_copies"
    for directory in (stream, jam, copies):
        directory.mkdir(parents=True)
    shutil.copy2(SOURCE, stream / "secure_jam_download.php")
    original = jam / filename
    original.write_bytes(content)
    original_hash = hashlib.sha256(content).digest()
    public_key_file = base / "public_key.pem"
    public_key_file.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env["MEDIA_DOWNLOAD_PUBLIC_KEY_FILE"] = str(public_key_file)
    env["MEDIA_DOWNLOAD_COPY_DIR"] = str(copies)
    php_command = [str(PHP)]
    windows_openssl = PHP.parent / "ext" / "php_openssl.dll"
    if os.name == "nt" and windows_openssl.is_file():
        php_command.extend(["-d", f"extension={windows_openssl}"])
    server = subprocess.Popen([*php_command, "-S", f"127.0.0.1:{port}", "-t", str(public)],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    opener = build_opener(ProxyHandler({}))
    endpoint = f"http://127.0.0.1:{port}/stream/secure_jam_download.php"

    def request(method, signed_ticket=None):
        if method == "HEAD":
            from urllib.parse import urlencode
            url = endpoint + "?" + urlencode({"code": code, "ticket": signed_ticket or ""})
            body = None
        else:
            url = endpoint
            body = json.dumps({"code": code, "ticket": signed_ticket or ""}).encode()
        req = Request(url, data=body, method=method,
                      headers={"Content-Type": "application/json"} if body else {})
        try:
            with opener.open(req, timeout=4) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()

    try:
        for _ in range(40):
            if server.poll() is not None:
                raise RuntimeError("PHP server stopped")
            try:
                request("POST")
                break
            except URLError:
                time.sleep(0.1)
        assert request("POST")[0] == 403
        valid_ticket = ticket("POST")
        payload, signature = valid_ticket.split(".")
        tampered = payload + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
        assert request("POST", tampered)[0] == 403
        assert request("POST", ticket("POST", expires=int(time.time()) - 5))[0] == 403
        assert request("POST", ticket("HEAD"))[0] == 403
        assert request("POST", ticket("POST", signed_code="other-video.mp4"))[0] == 403
        assert request("HEAD", ticket("HEAD"))[0] == 200
        assert request("POST", ticket("POST")) == (200, content)
        assert hashlib.sha256(original.read_bytes()).digest() == original_hash
        for _ in range(20):
            if not list(copies.iterdir()):
                break
            time.sleep(0.1)
        assert not list(copies.iterdir())
        print("Unsigned, tampered, expired, wrong-method and wrong-video tickets: 403")
        print("Signed HEAD/POST: 200; copy matches; original unchanged; copy removed")
    finally:
        server.terminate()
        server.wait(timeout=5)
