"""Genera el icono de la app (iPhone/Android) en static/, igual que el logo de la cabecera."""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(OUT, exist_ok=True)
S = 1024


def gradient(size):
    img = Image.new("RGB", (size, size))
    px = img.load()
    a, b = (124, 92, 255), (0, 200, 255)
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return img


def draw():
    img = gradient(S)
    d = ImageDraw.Draw(img, "RGBA")
    u, k = S / 40, 1.3  # misma cuadrícula de 40 que el SVG de la cabecera, ampliada un 30 %

    def P(v):  # coordenada del SVG -> píxeles (escala alrededor del centro)
        return (20 + (v - 20) * k) * u

    for cx in (10.7, 20, 29.3):  # carriles
        d.rounded_rectangle([P(cx - 1.7), P(9), P(cx + 1.7), P(31)], 1.7 * k * u, fill=(255, 255, 255, 90))
    for x, y in ((6.5, 21), (15.8, 13), (25.1, 18)):  # piezas de los faders
        d.rounded_rectangle([P(x), P(y), P(x + 8.4), P(y + 5)], 1.6 * k * u, fill=(255, 255, 255, 255))
    return img


for size in (180, 192, 512):
    draw().resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"icon-{size}.png"))
from mixer_i18n import tr  # noqa: E402

print(tr("Iconos creados en", "Icons created in"), OUT)
