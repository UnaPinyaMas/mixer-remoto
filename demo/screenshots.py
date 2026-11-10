"""Genera las capturas de los README (docs/es/*.png y docs/en/*.png) con Edge o Chrome sin ventana y el modo demo.

    python demo/screenshots.py

Necesita Pillow y Microsoft Edge o Google Chrome. Arranca la demo sola en el puerto 8091.

EN: Generates the README screenshots (docs/es/*.png and docs/en/*.png) with headless Edge or Chrome and the demo
mode. Needs Pillow and Microsoft Edge or Google Chrome. It starts the demo by itself on port 8091.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE, "docs")
PORT = 8091
URL = f"http://127.0.0.1:{PORT}"
LANGS = ("es", "en")
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
browser = next((b for b in BROWSERS if os.path.exists(b)), shutil.which("msedge") or shutil.which("chrome"))
if not browser:
    sys.exit("Edge / Chrome not found.")

env = dict(os.environ, DEMO_PORT=str(PORT), PYTHONIOENCODING="utf-8")
srv = subprocess.Popen([sys.executable, os.path.join(BASE, "demo", "demo_server.py")], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get(path):
    urllib.request.urlopen(URL + path, timeout=5).read()


def shot(lang, name, path, w, h, dark, talking=False):
    get("/demo/talk" + ("" if talking is None else f"?on={int(talking)}"))
    path += ("&" if "?" in path else "?") + f"lang={lang}&still=1"
    phone = w < 600                       # Edge/Chrome sin ventana no bajan de ~500 px: el móvil va en un marco y se recorta
    target = f"/frame?w={w}&h={h}&p={urllib.parse.quote(path)}" if phone else path
    out = os.path.join(DOCS, lang, name)
    prof = tempfile.mkdtemp()
    win_w = max(w, 640) if phone else w
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                    "--force-device-scale-factor=2", f"--window-size={win_w},{h}", "--virtual-time-budget=4500",
                    f"--blink-settings=preferredColorScheme={0 if dark else 1}",   # (0 = oscuro, 1 = claro en estos navegadores)
                    f"--screenshot={out}", URL + target], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    shutil.rmtree(prof, ignore_errors=True)
    if phone and os.path.exists(out):
        Image.open(out).crop((0, 0, w * 2, h * 2)).save(out, optimize=True)
    print("  ", lang, name, "ok" if os.path.exists(out) else "FAILED")


def phone_card(path, scale):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], int(44 * scale), fill=255)
    im.putalpha(m)
    return im


def hero(lang):
    """Imagen principal: tres móviles juntos."""
    names = ["screenshot-light.png", "screenshot-dark.png", "screenshot-edit.png"]
    if not all(os.path.exists(os.path.join(DOCS, lang, n)) for n in names):
        return
    ph = [phone_card(os.path.join(DOCS, lang, n), .62) for n in names]
    pad, gap = 70, 46
    W = sum(p.size[0] for p in ph) + gap * 2 + pad * 2
    H = max(p.size[1] for p in ph) + pad * 2
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    a, b = (28, 24, 62), (8, 60, 92)
    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    x = pad
    for p in ph:
        shadow = Image.new("RGBA", (p.size[0] + 80, p.size[1] + 80), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([40, 52, p.size[0] + 40, p.size[1] + 52], 40, fill=(0, 0, 0, 120))
        shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        bg.paste(shadow, (x - 40, pad - 40), shadow)
        bg.paste(p, (x, pad), p)
        x += p.size[0] + gap
    bg.save(os.path.join(DOCS, lang, "hero.png"), optimize=True)
    print("  ", lang, "hero.png ok")


try:
    for _ in range(30):
        try:
            get("/api/auth")
            break
        except Exception:
            time.sleep(0.3)
    for lang in LANGS:
        os.makedirs(os.path.join(DOCS, lang), exist_ok=True)
        get(f"/demo/lang?l={lang}")
        shot(lang, "screenshot-dark.png", "/", 390, 1070, True, talking=True)
        shot(lang, "screenshot-light.png", "/", 390, 1070, False, talking=False)
        shot(lang, "screenshot-edit.png", "/?edit=1", 390, 1070, True, talking=False)
        shot(lang, "screenshot-pin.png", "/?login=1&dots=4", 390, 780, True, talking=False)
        shot(lang, "screenshot-wide.png", "/", 1100, 1000, False, talking=False)
        hero(lang)
finally:
    srv.terminate()
