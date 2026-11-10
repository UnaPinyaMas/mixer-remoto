"""Modo demo: la interfaz del Mixer con datos ficticios, sin tocar el audio real ni necesitar Windows.

    python demo/demo_server.py            ->  http://localhost:8090

Sirve para probar el diseño, hacer capturas y desarrollar la interfaz en cualquier sistema.
"""
import hashlib
import io
import json
import math
import os
import time

from flask import Flask, Response, abort, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BASE, "static")
PORT = int(os.environ.get("DEMO_PORT", 8090))
app = Flask(__name__, static_folder=None)

APPS = [  # nombre del ejecutable, volumen, silenciado, "fase" para animar el medidor
    {"name": "Spotify.exe", "volume": 78, "muted": False, "ph": 0.0, "amp": 0.62},
    {"name": "Discord.exe", "volume": 90, "muted": False, "ph": 1.7, "amp": 0.30},
    {"name": "chrome.exe", "volume": 45, "muted": False, "ph": 3.1, "amp": 0.40},
    {"name": "FortniteClient-Win64-Shipping.exe", "volume": 36, "muted": False, "ph": 4.6, "amp": 0.55},
    {"name": "obs64.exe", "volume": 100, "muted": True, "ph": 2.2, "amp": 0.0},
]
STATE = {
    "master": {"volume": 72, "muted": False, "ph": 0.8, "amp": 0.7, "device": "Auriculares (HyperSound Pro Wireless)"},
    "mic": {"volume": 64, "muted": False, "ph": 5.0, "amp": 0.12, "device": "Micrófono (HyperSound Pro Wireless)"},
    "outputs": [
        {"id": "a", "name": "Auriculares (HyperSound Pro Wireless)", "active": True},
        {"id": "b", "name": "Altavoces (Realtek Audio)", "active": False},
        {"id": "c", "name": "LC27G5xT (NVIDIA High Definition Audio)", "active": False},
    ],
    "media": {"has": True, "title": "Lofi para estudiar", "artist": "Chillhop", "app": "Spotify",
              "playing": True, "prev": True, "next": True},
    "prefs": {"hidden": [], "pinned": ["Spotify.exe"],
              "duck": {"enabled": True, "level": 30, "threshold": 12, "triggers": ["Discord.exe"], "targets": ["Spotify.exe"]}},
    "rpc": {"configured": True, "connected": True, "channel": True, "channel_name": "Sala de juegos",
            "speaking": 0, "status": "Conectado a Discord"},
    "mute_all": False,
}


def peak(ph, amp, t):
    """Nivel ficticio que sube y baja como música."""
    if amp <= 0:
        return 0
    v = (math.sin(t * 2.3 + ph) * 0.5 + 0.5) * (math.sin(t * 0.7 + ph * 2) * 0.3 + 0.7)
    return int(max(0, min(100, v * amp * 100)))


FORCE_TALK = None   # None = alterna sola; True/False = fijo (para las capturas)


def snapshot():
    t = time.time()
    talking = FORCE_TALK if FORCE_TALK is not None else int(t / 4) % 2 == 1   # cada 4 s alguien habla y la música baja
    apps = []
    for a in APPS:
        ducked = talking and STATE["prefs"]["duck"]["enabled"] and a["name"] in STATE["prefs"]["duck"]["targets"]
        vol = round(a["volume"] * (STATE["prefs"]["duck"]["level"] / 100)) if ducked else a["volume"]
        apps.append({"name": a["name"], "volume": vol, "muted": a["muted"], "ducked": bool(ducked),
                     "peak": 0 if a["muted"] else peak(a["ph"], a["amp"], t)})
    snap = json.loads(json.dumps(STATE))
    snap["master"]["peak"] = peak(STATE["master"]["ph"], STATE["master"]["amp"], t)
    snap["mic"]["peak"] = peak(STATE["mic"]["ph"], STATE["mic"]["amp"], t)
    snap["apps"] = sorted(apps, key=lambda a: a["name"].lower())
    snap["no_output"] = False
    snap["ducking"] = talking and STATE["prefs"]["duck"]["enabled"]
    snap["rpc"]["speaking"] = 1 if talking else 0
    snap["voice"] = {"level": 0, "threshold": 12, "calibrating": False}
    return snap


@app.route("/")
def index():
    """/?login=1&dots=4 pantalla del PIN · /?edit=1 modo edición · /?cal=1 sin barra de acciones extra."""
    q = request.args
    name = "login.html" if q.get("login") else "index.html"
    html = open(os.path.join(STATIC, name), encoding="utf-8").read()
    extra = ""
    if q.get("edit"):
        extra += "setTimeout(()=>document.getElementById('editBtn').click(),700);"
    if q.get("dots"):
        extra += "".join(f"add('{d}');" for d in "135792"[: int(q["dots"])])
    if q.get("still"):
        # para capturas: en vez de la conexión continua, el estado llega una sola vez
        stub = ("<script>window.EventSource=class{constructor(){setTimeout(()=>fetch('/api/state').then(r=>r.json())"
                ".then(s=>this.onmessage&&this.onmessage({data:JSON.stringify(s)})),50)}addEventListener(){}close(){}};</script>")
        html = html.replace("<title>", stub + "<title>", 1)
    if extra:
        html = html.replace("</body>", f"<script>{extra}</script></body>")
    return Response(html, mimetype="text/html")


@app.route("/frame")
def frame():
    """Página con un marco de ancho/alto exactos: así el diseño de móvil se aplica aunque la ventana sea más ancha."""
    w, h, p = int(request.args.get("w", 390)), int(request.args.get("h", 900)), request.args.get("p", "/")
    return Response(f"<!doctype html><meta charset=utf-8><body style='margin:0;background:#888'>"
                    f"<iframe src='{p}' width={w} height={h} style='border:0;display:block'></iframe>", mimetype="text/html")


@app.route("/demo/talk")
def demo_talk():
    global FORCE_TALK
    v = request.args.get("on")
    FORCE_TALK = None if v is None else v == "1"
    return jsonify(talk=FORCE_TALK)


@app.route("/static/<path:p>")
def static_files(p):
    return send_from_directory(STATIC, p)


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC, "manifest.webmanifest")


@app.route("/api/state")
def state():
    return jsonify(snapshot())


@app.route("/api/auth")
def auth():
    return jsonify(ok=True)


@app.route("/api/stream")
def stream():
    def gen():
        yield "retry: 1500\n\n"
        while True:
            yield f"data: {json.dumps(snapshot(), separators=(',', ':'))}\n\n"
            time.sleep(0.1)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.route("/api/icon/<name>")
def icon(name):
    """Icono ficticio: cuadrado de color con la inicial (en el Mixer real se usa el icono del programa)."""
    from PIL import Image, ImageDraw, ImageFont
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16) % 360
    import colorsys
    c1 = tuple(int(x * 255) for x in colorsys.hls_to_rgb(h / 360, .55, .8))
    c2 = tuple(int(x * 255) for x in colorsys.hls_to_rgb(((h + 40) % 360) / 360, .45, .85))
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = img.load()
    for y in range(S):
        for x in range(S):
            k = (x + y) / (2 * S)
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3)) + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([8, 8, S - 8, S - 8], 28, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 64)
    except OSError:
        font = ImageFont.load_default()
    d.text((S / 2, S / 2), name[0].upper(), fill="white", font=font, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return Response(buf.getvalue(), mimetype="image/png")


@app.route("/api/volume", methods=["POST"])
def volume():
    d = request.get_json(force=True)
    t = d.get("target")
    obj = STATE["master"] if t == "master" else STATE["mic"] if t == "mic" else next((a for a in APPS if a["name"] == t), None)
    if obj is None:
        abort(404)
    for k in ("volume", "muted"):
        if k in d:
            obj[k] = d[k]
    return jsonify(ok=True)


@app.route("/api/output", methods=["POST"])
def output():
    i = request.get_json(force=True).get("id")
    for o in STATE["outputs"]:
        o["active"] = o["id"] == i
    return jsonify(ok=True)


@app.route("/api/media", methods=["POST"])
def media():
    if request.get_json(force=True).get("action") == "play_pause":
        STATE["media"]["playing"] = not STATE["media"]["playing"]
    return jsonify(ok=True)


@app.route("/api/mute_all", methods=["POST"])
def mute_all():
    on = bool(request.get_json(force=True).get("on"))
    STATE["mute_all"] = on
    for a in APPS:
        a["muted"] = on
    return jsonify(ok=True)


@app.route("/api/prefs", methods=["POST"])
def prefs():
    d = request.get_json(force=True)
    for key in ("hidden", "pinned"):
        if key in d:
            lst = STATE["prefs"][key]
            if d[key] and d["name"] not in lst:
                lst.append(d["name"])
            elif not d[key] and d["name"] in lst:
                lst.remove(d["name"])
    return jsonify(ok=True)


@app.route("/api/duck", methods=["POST"])
def duck():
    d = request.get_json(force=True)
    duck_cfg = STATE["prefs"]["duck"]
    for k in ("enabled", "level", "threshold"):
        if k in d:
            duck_cfg[k] = d[k]
    for key, mine, other in (("trigger", "triggers", "targets"), ("target", "targets", "triggers")):
        r = d.get(key)
        if isinstance(r, dict):
            lst = duck_cfg[mine]
            if r.get("on") and r["name"] not in lst:
                lst.append(r["name"])
                if r["name"] in duck_cfg[other]:
                    duck_cfg[other].remove(r["name"])
            elif not r.get("on") and r["name"] in lst:
                lst.remove(r["name"])
    return jsonify(ok=True)


if __name__ == "__main__":
    print(f"\n  Mixer (modo demo, datos ficticios):  http://localhost:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, threaded=True)
