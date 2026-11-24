"""index.html（Claudeのアプリ用）から、GitHub Pages用のスマホアプリ版をdocs/に作る。

使い方：python3 build.py
"""
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).parent
SITE = ROOT / "docs"
SITE.mkdir(exist_ok=True)

# ---- index.html：<head>を付けて普通のHTMLにする ----
src = (ROOT / "index.html").read_text(encoding="utf-8")
head_part, body_part = src.split("<main>", 1)
head_part = re.sub(r'<meta name="claude:[^>]*>\n?', "", head_part)

html = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#d9480f">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="毎日の習慣">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon-192.png">
<style>
  :root {{ padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }}
  [hidden] {{ display: none !important; }}
</style>
{head_part.strip()}
</head>
<body>
<main>{body_part.rstrip()}
<script>
// オフラインでも開けるようにする
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
</script>
</body>
</html>
"""
(SITE / "index.html").write_text(html, encoding="utf-8")

# ---- manifest：ホーム画面に追加したときの名前・アイコン ----
(SITE / "manifest.webmanifest").write_text("""{
  "name": "毎日の習慣",
  "short_name": "習慣",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#f5f3ef",
  "theme_color": "#d9480f",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
""", encoding="utf-8")

# ---- service worker：一度開けばオフラインでも動く。ネットがあれば最新版を取りに行く ----
(SITE / "sw.js").write_text("""const CACHE = "workout-app-v1";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-180.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
  self.skipWaiting();
});
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));

// ネット優先、つながらなければ保存しておいた版を出す
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
""", encoding="utf-8")


# ---- アイコン：オレンジ地に白いダンベル（外部ライブラリなしでPNGを書く） ----
def icon(size: int) -> bytes:
    bg = (217, 72, 15)
    fg = (255, 255, 255)
    s = size / 100  # 100×100の設計図を拡大する
    rects = [  # (x0, y0, x1, y1)
        (22, 47, 78, 53),  # 持ち手
        (14, 32, 22, 68), (24, 26, 32, 74),  # 左のおもり
        (68, 26, 76, 74), (78, 32, 86, 68),  # 右のおもり
    ]
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            px, py = x / s, y / s
            inside = any(x0 <= px < x1 and y0 <= py < y1 for x0, y0, x1, y1 in rects)
            row += bytes(fg if inside else bg)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


for n in (180, 192, 512):
    (SITE / f"icon-{n}.png").write_bytes(icon(n))

print("docs/ を作成しました")
