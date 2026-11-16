<?php
// The webapp checks the paid entitlement, then signs a short-lived media ticket.
// This endpoint holds only the corresponding public key, never an API/secret key.

$method = $_SERVER['REQUEST_METHOD'] ?? '';
if ($method !== 'POST' && $method !== 'HEAD') {
    http_response_code(405);
    exit;
}

$publicKeyPath = getenv('MEDIA_DOWNLOAD_PUBLIC_KEY_FILE') ?: '';
if (!function_exists('openssl_pkey_get_public') || !$publicKeyPath || !is_readable($publicKeyPath)) {
    http_response_code(503);
    exit;
}
$publicKeyText = file_get_contents($publicKeyPath);
$publicKey = $publicKeyText === false ? false : openssl_pkey_get_public($publicKeyText);
$details = $publicKey ? openssl_pkey_get_details($publicKey) : false;
if (!$details || $details['type'] !== OPENSSL_KEYTYPE_RSA || $details['bits'] < 2048) {
    http_response_code(503);
    exit;
}

$body = $method === 'POST' ? json_decode(file_get_contents('php://input'), true) : null;
$code = $method === 'HEAD' ? ($_GET['code'] ?? '') : (is_array($body) ? ($body['code'] ?? '') : '');
$ticket = $method === 'HEAD' ? ($_GET['ticket'] ?? '') : (is_array($body) ? ($body['ticket'] ?? '') : '');
if (!is_string($code) || strlen($code) < 6 || strlen($code) > 512) {
    http_response_code(400);
    exit;
}
if (!is_string($ticket) || strlen($ticket) > 4096 ||
    !preg_match('/^([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)$/D', $ticket, $parts)) {
    http_response_code(403);
    exit;
}
$decodeUrl64 = static function (string $value): string|false {
    return base64_decode(strtr($value, '-_', '+/') . str_repeat('=', (4 - strlen($value) % 4) % 4), true);
};
$payload = $decodeUrl64($parts[1]);
$signature = $decodeUrl64($parts[2]);
$claims = $payload === false ? null : json_decode($payload, true);
$now = time();
if ($signature === false || !is_array($claims) ||
    ($claims['v'] ?? null) !== 1 || ($claims['code'] ?? null) !== $code ||
    ($claims['method'] ?? null) !== $method ||
    !isset($claims['exp']) || !is_int($claims['exp']) ||
    $claims['exp'] <= $now || $claims['exp'] > $now + 90 ||
    openssl_verify($parts[1], $signature, $publicKey, OPENSSL_ALGO_SHA256) !== 1) {
    http_response_code(403);
    exit;
}

// Match the legacy code used by stream/jam_stream.php.
$plainAlphabet = 'MUbzFknEOsjG7HaKgYov.62d9VlRZfpyWcq_1D0PS3QT45LNiIAmCBx8teJrhX-uw';
$codedAlphabet = 'sY6ndv30.jHQVNBmEo5eLXKSGcFZ8R1bpDAa_iMlTuw9t2IUxgqO4kzrC7JyhWP-f';
$filename = '';
for ($i = 0, $length = strlen($code); $i < $length; $i++) {
    $position = strpos($codedAlphabet, $code[$i]);
    if ($position === false) {
        http_response_code(400);
        exit;
    }
    $filename .= $plainAlphabet[$position];
}
for ($i = 0; $i < 4 && str_ends_with($filename, 'a'); $i++) {
    $filename = substr($filename, 0, -1);
}
if (basename($filename) !== $filename ||
    !preg_match('/^[A-Za-z0-9._-]+\.mp4$/D', $filename)) {
    http_response_code(400);
    exit;
}

$jamDirectory = realpath(__DIR__ . '/../uploads/jam');
$source = $jamDirectory ? realpath($jamDirectory . DIRECTORY_SEPARATOR . $filename) : false;
if (!$source || !str_starts_with($source, $jamDirectory . DIRECTORY_SEPARATOR) || !is_file($source)) {
    http_response_code(404);
    exit;
}

if ($method === 'HEAD') {
    header('Content-Type: video/mp4');
    header('Content-Length: ' . filesize($source));
    header('Cache-Control: private, no-store');
    exit;
}

// This directory must be outside public_html and writable by PHP.
$copyDirectory = realpath(getenv('MEDIA_DOWNLOAD_COPY_DIR') ?: '/var/www/media/download_copies');
$publicDirectory = realpath(__DIR__ . '/..');
if (!$copyDirectory || !$publicDirectory ||
    str_starts_with($copyDirectory . DIRECTORY_SEPARATOR, $publicDirectory . DIRECTORY_SEPARATOR) ||
    !is_writable($copyDirectory)) {
    http_response_code(503);
    exit;
}
$copy = tempnam($copyDirectory, 'jam_');
if ($copy === false) {
    http_response_code(503);
    exit;
}
register_shutdown_function(static function () use ($copy): void {
    if (is_file($copy)) {
        @unlink($copy);
    }
});
if (!copy($source, $copy)) {
    http_response_code(500);
    exit;
}

header('Content-Type: video/mp4');
header('Content-Disposition: attachment; filename="fuzik-jam.mp4"');
header('Content-Length: ' . filesize($copy));
header('Cache-Control: private, no-store');
header('X-Content-Type-Options: nosniff');
$stream = fopen($copy, 'rb');
if ($stream === false) {
    http_response_code(500);
    exit;
}
fpassthru($stream);
fclose($stream);
