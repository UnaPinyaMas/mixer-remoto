"""Mixer remoto: controla el audio de Windows (salida, apps, micro y música) desde el móvil.

Usa solo librerías gratuitas y de código abierto: Flask + waitress (servidor), pycaw (audio de Windows),
winrt (controles multimedia), Pillow (iconos), zeroconf (mixer.local).

EN: Remote mixer: control Windows audio (output, per-app volume, mic and music) from your phone.
Built only on free, open-source libraries: Flask + waitress (server), pycaw (Windows audio), winrt (media controls),
Pillow (icons), zeroconf (mixer.local). Code comments are mostly in Spanish.
"""
import asyncio
import hashlib
import hmac
import json
import os
import queue
import re
import socket
import threading
import time
from collections import OrderedDict

import comtypes
import psutil
import discord_rpc
from comtypes import CLSCTX_ALL
from mixer_i18n import tr
from flask import Flask, Response, abort, jsonify, request, send_file, send_from_directory
from pycaw.constants import DEVICE_STATE, EDataFlow, ERole
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
    IAudioMeterInformation,
    IAudioSessionControl2,
    IAudioSessionManager2,
    ISimpleAudioVolume,
)

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    )
except Exception:  # sin winrt: el resto funciona igual
    MediaManager = None

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")
ICON_DIR = os.path.join(BASE, "icons")
os.makedirs(ICON_DIR, exist_ok=True)

PORT = int(os.environ.get("MIXER_PORT", 8080))
HOSTNAME = "mixer"  # -> http://mixer.local:8080
HIDE_DEVICES = ("steam streaming",)  # dispositivos virtuales que no interesan

app = Flask(__name__, static_folder=None)

# ───────────────────────── COM ─────────────────────────
_tls = threading.local()


def com_init():
    if not getattr(_tls, "ok", False):
        comtypes.CoInitialize()
        _tls.ok = True


def default_dev(flow):
    enum = AudioUtilities.GetDeviceEnumerator()
    return enum.GetDefaultAudioEndpoint(flow, ERole.eMultimedia.value)


def activate(dev, iface):
    return dev.Activate(iface._iid_, CLSCTX_ALL, None).QueryInterface(iface)


# ───────────────────── Dispositivos ─────────────────────
_dev_cache = {"t": 0, "names": {}, "outputs": []}
_dev_lock = threading.Lock()


_dev_thread = None
_last_api = 0.0


def refresh_devices():
    """La lista de dispositivos tarda ~2 s en leerse: solo la primera vez se espera; luego la renueva un hilo."""
    global _dev_thread, _last_api
    _last_api = time.time()
    if _dev_cache["t"] == 0:
        _do_refresh()
    if _dev_thread is None:
        _dev_thread = threading.Thread(target=_dev_loop, daemon=True)
        _dev_thread.start()


def _dev_loop():
    com_init()
    while True:
        time.sleep(4)
        if time.time() - _last_api < 60:  # solo mientras alguien use el mixer
            try:
                _do_refresh()
            except Exception as e:
                print(tr("dispositivos:", "devices:"), e)


def _do_refresh():
    with _dev_lock:
        names, outputs = {}, []
        for flow, is_out in ((EDataFlow.eRender.value, True), (EDataFlow.eCapture.value, False)):
            for d in AudioUtilities.GetAllDevices(flow, DEVICE_STATE.ACTIVE.value):
                name = d.FriendlyName or "?"
                names[d.id] = name
                if is_out and not any(h in name.lower() for h in HIDE_DEVICES):
                    outputs.append({"id": d.id, "name": name})
        _dev_cache.update(t=time.time(), names=names, outputs=outputs)


# ─────────────────────── Sesiones ───────────────────────
_procs = {}  # pid -> (nombre, exe)
_exes = {}  # nombre -> exe (para sacar iconos)
_procs_t = time.time()


def proc_info(pid):
    global _procs_t
    if time.time() - _procs_t > 60:
        _procs.clear()
        _procs_t = time.time()
    if pid not in _procs:
        try:
            p = psutil.Process(pid)
            _procs[pid] = (p.name(), p.exe())
        except Exception:
            _procs[pid] = None
    return _procs[pid]


_epoch = 0  # sube al cambiar de salida de audio para renovar el gestor de sesiones en caché


def _session_manager():
    """El gestor de sesiones se reutiliza unos segundos por hilo: crearlo cada vez es lo más caro."""
    c = getattr(_tls, "mgr", None)
    now = time.time()
    if c is None or c[1] != _epoch or now - c[2] > 5:
        c = (activate(default_dev(EDataFlow.eRender.value), IAudioSessionManager2), _epoch, now)
        _tls.mgr = c
    return c[0]


def iter_sessions():
    """(nombre_exe, control) de cada sesión de audio del dispositivo de salida activo."""
    try:
        en = _session_manager().GetSessionEnumerator()
        count = en.GetCount()
    except comtypes.COMError:
        _tls.mgr = None
        return
    for i in range(count):
        try:
            ctl = en.GetSession(i)
            ctl2 = ctl.QueryInterface(IAudioSessionControl2)
            pid = ctl2.GetProcessId()
            if pid == 0 or ctl2.GetState() == 2:  # sistema / caducada
                continue
            info = proc_info(pid)
            if not info:
                continue
            _exes[info[0]] = info[1]
            yield info[0], ctl
        except comtypes.COMError:
            continue


def pk(x):
    return int(round(x * 100))


def snapshot():
    com_init()
    refresh_devices()
    names = _dev_cache["names"]

    try:
        dev = default_dev(EDataFlow.eRender.value)
        ev = activate(dev, IAudioEndpointVolume)
        meter = activate(dev, IAudioMeterInformation)
        out_id = dev.GetId()
        master = {
            "volume": pk(ev.GetMasterVolumeLevelScalar()),
            "muted": bool(ev.GetMute()),
            "peak": pk(meter.GetPeakValue()),
            "device": names.get(out_id, ""),
        }
        no_output = False
    except comtypes.COMError:   # no hay ninguna salida de audio activa (auriculares apagados, monitor en reposo...)
        out_id, no_output = None, True
        master = {"volume": 0, "muted": False, "peak": 0, "device": ""}
    snap = {
        "master": master,
        "no_output": no_output,
        "outputs": [dict(o, active=(o["id"] == out_id)) for o in _dev_cache["outputs"]],
        "mic": None,
    }
    try:
        mdev = default_dev(EDataFlow.eCapture.value)
        mev = activate(mdev, IAudioEndpointVolume)
        mm = activate(mdev, IAudioMeterInformation)
        snap["mic"] = {
            "volume": pk(mev.GetMasterVolumeLevelScalar()),
            "muted": bool(mev.GetMute()),
            "peak": pk(mm.GetPeakValue()),
            "device": names.get(mdev.GetId(), ""),
        }
    except comtypes.COMError:
        pass

    apps = OrderedDict()
    for name, ctl in iter_sessions():
        try:
            sv = ctl.QueryInterface(ISimpleAudioVolume)
            mi = ctl.QueryInterface(IAudioMeterInformation)
            a = apps.setdefault(
                name,
                {"name": name, "volume": pk(sv.GetMasterVolume()), "muted": bool(sv.GetMute()), "peak": 0,
                 "ducked": name in duck_states and duck_states[name]["factor"] < 0.98},
            )
            a["peak"] = max(a["peak"], pk(mi.GetPeakValue()))
        except comtypes.COMError:
            continue
    snap["apps"] = sorted(apps.values(), key=lambda a: a["name"].lower())
    snap["media"] = media_state
    snap["prefs"] = json.loads(json.dumps(prefs))
    snap["ducking"] = duck_active
    snap["rpc"] = {k: discord_rpc.state[k] for k in ("configured", "connected", "channel", "channel_name", "speaking", "code", "detail", "status")}
    snap["voice"] = {"level": min(150, int(round(duck_level * 100))), "threshold": prefs["duck"]["threshold"],
                     "calibrating": time.time() < _calib_until}
    snap["mute_all"] = _saved_mutes is not None
    return snap


def set_target(target, data):
    com_init()
    vol = data.get("volume")
    muted = data.get("muted")
    if target in ("master", "mic"):
        flow = EDataFlow.eRender.value if target == "master" else EDataFlow.eCapture.value
        ev = activate(default_dev(flow), IAudioEndpointVolume)
        if vol is not None:
            ev.SetMasterVolumeLevelScalar(max(0, min(100, vol)) / 100, None)
        if muted is not None:
            ev.SetMute(1 if muted else 0, None)
    else:
        for name, ctl in iter_sessions():
            if name != target:
                continue
            sv = ctl.QueryInterface(ISimpleAudioVolume)
            if vol is not None:
                sv.SetMasterVolume(max(0, min(100, vol)) / 100, None)
            if muted is not None:
                sv.SetMute(1 if muted else 0, None)
    wake.set()


# ─────────── Preferencias (ocultar / fijar apps) ───────────
PREFS_FILE = os.path.join(BASE, "prefs.json")
_prefs_lock = threading.Lock()


DUCK_DEFAULT = {"enabled": False, "level": 30, "threshold": 12, "triggers": ["Discord.exe"], "targets": ["brave.exe"]}


def _load_prefs():
    prefs = {"hidden": [], "pinned": [], "duck": json.loads(json.dumps(DUCK_DEFAULT))}
    try:
        with open(PREFS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        prefs["hidden"] = list(d.get("hidden", []))
        prefs["pinned"] = list(d.get("pinned", []))
        duck = d.get("duck", {})
        prefs["duck"].update({k: duck[k] for k in DUCK_DEFAULT if k in duck})
    except Exception:
        pass
    return prefs


prefs = _load_prefs()


def _save_prefs():
    tmp = PREFS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PREFS_FILE)


# ─────────────────── Silenciar todo ───────────────────
_saved_mutes = None  # None = normal; dict = "silenciar todo" activo (estado previo de cada app)


def mute_all(on):
    global _saved_mutes
    com_init()
    if on:
        saved = _saved_mutes if _saved_mutes is not None else {}
        for name, ctl in iter_sessions():
            sv = ctl.QueryInterface(ISimpleAudioVolume)
            saved[name] = saved.get(name, False) or bool(sv.GetMute())
            sv.SetMute(1, None)
        _saved_mutes = saved
    elif _saved_mutes is not None:
        for name, ctl in iter_sessions():
            if name in _saved_mutes:  # las que ya estaban silenciadas siguen igual
                ctl.QueryInterface(ISimpleAudioVolume).SetMute(1 if _saved_mutes[name] else 0, None)
        _saved_mutes = None
    wake.set()


# ─────────── Bajar música al hablar (ducking) ───────────
DUCK_ATTACK = 0.2       # el nivel debe superar el umbral este tiempo seguido (ignora pitidos y avisos cortos)
DUCK_HOLD = 1.2         # segundos de silencio antes de volver a subir (evita subir y bajar entre palabras)
CALIBRATE_S = 4.0       # duración de "Medir silencio"
duck_level = 0.0        # nivel actual de la app de voz (para la barra en directo)
_calib_until = 0.0      # mientras sea futuro: midiendo el ruido de fondo
_calib_max = 0.0
DUCK_DOWN_S, DUCK_UP_S = 0.25, 1.0
DUCK_FILE = os.path.join(BASE, "duck_state.json")
duck_states = {}        # app -> {"orig": volumen original, "factor": 1..nivel, "set": último valor puesto por nosotros}
duck_pending = {}       # volúmenes originales por devolver (app cerrada mientras estaba bajada, o reinicio)
duck_active = False
_duck_released = set()  # apps que el usuario tocó a mano: no se vuelven a bajar hasta que termine la voz


def _duck_persist():
    """Guarda los volúmenes originales: si el servidor se cae a medias, se devuelven al arrancar."""
    data = {n: s["orig"] for n, s in duck_states.items()}
    data.update(duck_pending)
    try:
        if data:
            with open(DUCK_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        elif os.path.exists(DUCK_FILE):
            os.remove(DUCK_FILE)
    except OSError:
        pass


def _set_app_volume(ctls, v):
    for c in ctls:
        c.QueryInterface(ISimpleAudioVolume).SetMasterVolume(max(0.0, min(1.0, v)), None)


def duck_loop():
    global duck_active, duck_level, _calib_until, _calib_max
    com_init()
    above_since = None
    try:
        with open(DUCK_FILE, encoding="utf-8") as f:
            duck_pending.update({k: float(v) for k, v in json.load(f).items()})
    except Exception:
        pass
    last_sound, last_t = 0.0, time.time()
    while True:
        time.sleep(0.1)
        now = time.time()
        dt, last_t = now - last_t, now
        try:
            cfg = prefs["duck"]
            if not cfg["enabled"] and not duck_states and not duck_pending:
                _duck_released.clear()
                duck_level, _calib_until, above_since = 0.0, 0.0, None
                if duck_active:
                    duck_active = False
                    wake.set()
                time.sleep(0.4)
                continue
            by_name = {}
            for name, ctl in iter_sessions():
                by_name.setdefault(name, []).append(ctl)

            # devolver volúmenes pendientes cuando la app vuelve a estar abierta
            for name in [n for n in duck_pending if n in by_name]:
                cur = by_name[name][0].QueryInterface(ISimpleAudioVolume).GetMasterVolume()
                if cur < duck_pending[name] - 0.01:
                    _set_app_volume(by_name[name], duck_pending[name])
                del duck_pending[name]
                _duck_persist()

            enabled = bool(cfg["enabled"])
            triggers = set(cfg["triggers"])
            targets = set(cfg["targets"]) - triggers

            # nivel de la app de voz (el mayor de sus sesiones). Con Discord conectado por RPC no se mide su volumen
            rpc_live = discord_rpc.state["connected"]
            meter_triggers = triggers - {"Discord.exe"} if rpc_live else triggers
            vlevel = 0.0
            if enabled:
                for name in meter_triggers:
                    for ctl in by_name.get(name, []):
                        if ctl.QueryInterface(ISimpleAudioVolume).GetMute():
                            continue
                        vlevel = max(vlevel, ctl.QueryInterface(IAudioMeterInformation).GetPeakValue())
            duck_level = vlevel   # (la barra en directo se envía con el ciclo normal de 10 veces por segundo)

            # "Medir silencio": durante unos segundos mide el ruido de fondo y fija el umbral por encima
            if _calib_until and now >= _calib_until:
                cfg["threshold"] = max(3, min(90, int(_calib_max * 100 * 1.3) + 3))
                _calib_until = 0.0
                with _prefs_lock:
                    _save_prefs()
                wake.set()

            thr = max(1, min(90, int(cfg["threshold"]))) / 100
            speaking = False
            if now < _calib_until:
                _calib_max = max(_calib_max, vlevel)
                above_since = None
            elif vlevel > thr:
                if above_since is None:
                    above_since = now
                speaking = now - above_since >= DUCK_ATTACK
            else:
                above_since = None
            if enabled and rpc_live and "Discord.exe" in triggers and discord_rpc.state["speaking"] > 0:
                speaking = True       # alguien (que no eres tú) habla en tu canal de voz de Discord
            if speaking:
                last_sound = now
            want = enabled and (speaking or now - last_sound < DUCK_HOLD)
            if not want:
                _duck_released.clear()
            level = max(0, min(90, int(cfg["level"]))) / 100
            goal = level if want else 1.0
            span = max(0.05, 1 - level)

            # apps bajadas que ya no deben estarlo: cerradas, sin rol o función desactivada
            for name in list(duck_states):
                st = duck_states[name]
                if name not in by_name:
                    duck_pending[name] = st["orig"]
                    del duck_states[name]
                    _duck_persist()
                elif not enabled or name not in targets:
                    cur = by_name[name][0].QueryInterface(ISimpleAudioVolume).GetMasterVolume()
                    if abs(cur - st["set"]) <= 0.015:   # si la tocaste tú, se respeta
                        _set_app_volume(by_name[name], st["orig"])
                    del duck_states[name]
                    _duck_persist()

            for name in targets & set(by_name):
                if name in _duck_released:
                    continue
                ctls = by_name[name]
                cur = ctls[0].QueryInterface(ISimpleAudioVolume).GetMasterVolume()
                st = duck_states.get(name)
                if st is None:
                    if not want or goal >= 0.999:
                        continue
                    st = duck_states[name] = {"orig": cur, "factor": 1.0, "set": cur}
                    _duck_persist()
                elif abs(cur - st["set"]) > 0.015:      # el usuario movió el volumen: manda lo suyo
                    del duck_states[name]
                    _duck_released.add(name)
                    _duck_persist()
                    continue
                f = st["factor"]
                if goal < f:
                    f = max(goal, f - span * dt / DUCK_DOWN_S)
                else:
                    f = min(goal, f + span * dt / DUCK_UP_S)
                if f >= 0.9999 and goal >= 1.0:          # ya terminó de subir: volumen exacto de antes
                    _set_app_volume(ctls, st["orig"])
                    del duck_states[name]
                    _duck_persist()
                    continue
                _set_app_volume(ctls, st["orig"] * f)
                st["factor"] = f
                st["set"] = ctls[0].QueryInterface(ISimpleAudioVolume).GetMasterVolume()

            now_active = any(s["factor"] < 0.98 for s in duck_states.values())
            if now_active != duck_active:
                duck_active = now_active
                wake.set()
        except Exception as e:
            print(tr("bajar música:", "ducking:"), e)
            time.sleep(1)


# ─────────────────────── Música ───────────────────────
media_state = {"has": False}
_media_loop = None


async def media_poll():
    global media_state
    mgr = await MediaManager.request_async()
    while True:
        try:
            s = mgr.get_current_session()
            if s is None:
                new = {"has": False}
            else:
                p = await s.try_get_media_properties_async()
                info = s.get_playback_info()
                c = info.controls
                new = {
                    "has": True,
                    "title": p.title or "",
                    "artist": p.artist or "",
                    "app": (s.source_app_user_model_id or "").replace(".exe", ""),
                    "playing": int(info.playback_status) == 4,
                    "prev": bool(c.is_previous_enabled),
                    "next": bool(c.is_next_enabled),
                }
        except Exception:
            new = {"has": False}
        if new != media_state:
            media_state = new
            wake.set()
        await asyncio.sleep(0.5)


def media_thread():
    global _media_loop
    _media_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_media_loop)
    _media_loop.run_until_complete(media_poll())


# ───────────────── Tiempo real (SSE) ─────────────────
subs, subs_lock, wake = set(), threading.Lock(), threading.Event()
_last = None


def broadcast(text):
    with subs_lock:
        targets = list(subs)
    for q in targets:
        try:
            q.put_nowait(text)
        except queue.Full:
            try:
                q.get_nowait()
                q.put_nowait(text)
            except Exception:
                pass


def engine():
    """Lee el estado de audio ~10 veces/s y lo envía a los móviles conectados si cambió."""
    global _last
    com_init()
    while True:
        if not subs:
            wake.wait(1.0)
            wake.clear()
            if not subs:
                continue
        try:
            text = json.dumps(snapshot(), separators=(",", ":"))
            if text != _last:
                _last = text
                broadcast(text)
        except Exception as e:
            print("engine:", e)
        time.sleep(0.03)        # nunca más de ~30 lecturas/s, pase lo que pase
        wake.wait(0.07)
        wake.clear()


@app.route("/api/stream")
def stream():
    global _last
    q = queue.Queue(maxsize=4)
    with subs_lock:
        subs.add(q)
    _last = None  # fuerza un estado completo para el cliente nuevo
    wake.set()

    def gen():
        try:
            yield "retry: 1500\n\n"
            while True:
                try:
                    yield f"data: {q.get(timeout=10)}\n\n"
                except queue.Empty:
                    yield "event: ping\ndata: 1\n\n"
        finally:
            with subs_lock:
                subs.discard(q)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ───────────────────────── API ─────────────────────────
@app.route("/api/state")
def state():
    return jsonify(snapshot())


@app.route("/api/volume", methods=["POST"])
def api_volume():
    data = request.get_json(force=True)
    set_target(data.get("target"), data)
    return jsonify(ok=True)


@app.route("/api/mute_all", methods=["POST"])
def api_mute_all():
    mute_all(bool(request.get_json(force=True).get("on")))
    return jsonify(ok=True)


@app.route("/api/prefs", methods=["POST"])
def api_prefs():
    d = request.get_json(force=True)
    name = d.get("name")
    if not isinstance(name, str) or not name:
        abort(400)
    with _prefs_lock:
        for key in ("hidden", "pinned"):
            if key in d:
                lst = prefs[key]
                if d[key] and name not in lst:
                    lst.append(name)
                elif not d[key] and name in lst:
                    lst.remove(name)
        _save_prefs()
    wake.set()
    return jsonify(ok=True)


@app.route("/api/duck", methods=["POST"])
def api_duck():
    d = request.get_json(force=True)
    with _prefs_lock:
        duck = prefs["duck"]
        if "enabled" in d:
            duck["enabled"] = bool(d["enabled"])
        if "level" in d:
            duck["level"] = max(0, min(90, int(d["level"])))
        if "threshold" in d:
            duck["threshold"] = max(1, min(90, int(d["threshold"])))
        if d.get("calibrate"):
            global _calib_until, _calib_max
            _calib_max, _calib_until = 0.0, time.time() + CALIBRATE_S
        for key, mine, other in (("trigger", "triggers", "targets"), ("target", "targets", "triggers")):
            role = d.get(key)
            if isinstance(role, dict) and isinstance(role.get("name"), str) and role["name"]:
                name = role["name"]
                if role.get("on"):
                    if name not in duck[mine]:
                        duck[mine].append(name)
                    if name in duck[other]:       # una app no puede ser voz y a la vez bajarse
                        duck[other].remove(name)
                elif name in duck[mine]:
                    duck[mine].remove(name)
        _save_prefs()
    wake.set()
    return jsonify(ok=True)


@app.route("/api/output", methods=["POST"])
def api_output():
    dev_id = request.get_json(force=True).get("id")
    if dev_id not in {o["id"] for o in _dev_cache["outputs"]}:
        abort(400)
    com_init()
    AudioUtilities.SetDefaultDevice(
        dev_id, [ERole.eConsole, ERole.eMultimedia, ERole.eCommunications]
    )
    global _epoch
    _epoch += 1
    wake.set()
    return jsonify(ok=True)


@app.route("/api/media", methods=["POST"])
def api_media():
    action = request.get_json(force=True).get("action")
    if MediaManager is None or _media_loop is None:
        abort(503)

    async def run():
        s = (await MediaManager.request_async()).get_current_session()
        if s is None:
            return
        if action == "play_pause":
            await s.try_toggle_play_pause_async()
        elif action == "next":
            await s.try_skip_next_async()
        elif action == "prev":
            await s.try_skip_previous_async()

    asyncio.run_coroutine_threadsafe(run(), _media_loop).result(timeout=4)
    wake.set()
    return jsonify(ok=True)


# ───────────────────── Iconos de apps ─────────────────────
def extract_icon(exe, out, size=128):
    """Saca el icono real (hasta 256px) de un .exe y lo guarda como PNG."""
    try:
        import ctypes
        from ctypes import wintypes as w

        from PIL import Image

        u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
        vp = ctypes.c_void_p
        u32.PrivateExtractIconsW.argtypes = [w.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                             ctypes.POINTER(vp), ctypes.POINTER(w.UINT), w.UINT, w.UINT]
        u32.PrivateExtractIconsW.restype = w.UINT
        u32.DrawIconEx.argtypes = [vp, ctypes.c_int, ctypes.c_int, vp, ctypes.c_int, ctypes.c_int, w.UINT, vp, w.UINT]
        u32.DestroyIcon.argtypes = [vp]
        g32.CreateCompatibleDC.argtypes, g32.CreateCompatibleDC.restype = [vp], vp
        g32.SelectObject.argtypes, g32.SelectObject.restype = [vp, vp], vp
        g32.DeleteObject.argtypes = [vp]
        g32.DeleteDC.argtypes = [vp]

        class BIH(ctypes.Structure):
            _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG), ("biPlanes", w.WORD),
                        ("biBitCount", w.WORD), ("biCompression", w.DWORD), ("biSizeImage", w.DWORD),
                        ("biXPelsPerMeter", w.LONG), ("biYPelsPerMeter", w.LONG),
                        ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD)]

        g32.CreateDIBSection.argtypes = [vp, ctypes.POINTER(BIH), w.UINT, ctypes.POINTER(vp), vp, w.DWORD]
        g32.CreateDIBSection.restype = vp

        hicon, iid = vp(), w.UINT()
        n = u32.PrivateExtractIconsW(exe, 0, size, size, ctypes.byref(hicon), ctypes.byref(iid), 1, 0)
        if n in (0, 0xFFFFFFFF) or not hicon.value:
            return False
        bih = BIH(ctypes.sizeof(BIH), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = vp()
        dc = g32.CreateCompatibleDC(None)
        bmp = g32.CreateDIBSection(dc, ctypes.byref(bih), 0, ctypes.byref(bits), None, 0)
        old = g32.SelectObject(dc, bmp)
        u32.DrawIconEx(dc, 0, 0, hicon, size, size, 0, None, 3)  # DI_NORMAL
        raw = bytearray(ctypes.string_at(bits.value, size * size * 4))
        g32.SelectObject(dc, old)
        g32.DeleteObject(bmp)
        g32.DeleteDC(dc)
        u32.DestroyIcon(hicon)

        if max(raw[3::4]) == 0:  # icono sin canal alfa
            raw[3::4] = b"\xff" * (size * size)
        else:  # des-premultiplicar
            for i in range(0, len(raw), 4):
                a = raw[i + 3]
                if 0 < a < 255:
                    raw[i] = min(255, raw[i] * 255 // a)
                    raw[i + 1] = min(255, raw[i + 1] * 255 // a)
                    raw[i + 2] = min(255, raw[i + 2] * 255 // a)
        Image.frombuffer("RGBA", (size, size), bytes(raw), "raw", "BGRA", 0, 1).save(out, "PNG")
        return True
    except Exception as e:
        print(tr("icono:", "icon:"), exe, e)
        return False


@app.route("/api/icon/<name>")
def api_icon(name):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    path = os.path.join(ICON_DIR, safe + ".png")
    if not os.path.exists(path):
        exe = _exes.get(name)
        if not exe or not extract_icon(exe, path):
            abort(404)
    resp = send_file(path, mimetype="image/png")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


# ──────────────────── Seguridad: PIN ────────────────────
# El PIN se crea en el PC con setup-pin.bat (se guarda solo su "huella", nunca el PIN). Sin pin.json, el
# acceso es libre. Con PIN: cada dispositivo lo introduce una vez y recibe una cookie firmada de 90 días.
PIN_FILE = os.environ.get("MIXER_PIN_FILE", os.path.join(BASE, "pin.json"))
COOKIE = "mixer_auth"
COOKIE_DAYS = 90
MAX_FAILS = 5
_pin_cache = {"mtime": None, "cfg": None}
_fails = {}   # ip -> {"n": fallos seguidos, "until": bloqueado hasta, "strikes": bloqueos acumulados}
_PRIVATE = re.compile(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|127\.|169\.254\.|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.)")


def pin_cfg():
    """None = sin PIN. Si pin.json existe pero está roto, se bloquea todo (nunca se deja abierto por error)."""
    try:
        m = os.path.getmtime(PIN_FILE)
    except OSError:
        _pin_cache.update(mtime=None, cfg=None)
        return None
    if _pin_cache["mtime"] != m:
        try:
            with open(PIN_FILE, encoding="utf-8") as f:
                c = json.load(f)
            c["_salt"], c["_secret"] = bytes.fromhex(c["salt"]), bytes.fromhex(c["secret"])
            c["_hash"] = bytes.fromhex(c["hash"])
            _pin_cache.update(mtime=m, cfg=c)
        except Exception:
            _pin_cache.update(mtime=m, cfg={"invalid": True})
    return _pin_cache["cfg"]


def is_loopback():
    return request.remote_addr in ("127.0.0.1", "::1")


def _sign(cfg, exp):
    return hmac.new(cfg["_secret"], f"{exp}.{cfg['hash']}".encode(), "sha256").hexdigest()


def set_auth_cookie(resp, cfg):
    exp = int(time.time()) + COOKIE_DAYS * 86400
    resp.set_cookie(COOKIE, f"{exp}.{_sign(cfg, exp)}", max_age=COOKIE_DAYS * 86400,
                    httponly=True, samesite="Lax", path="/")


def authed(cfg):
    if is_loopback():                      # desde el propio PC no se pide
        return True
    if cfg.get("invalid"):
        return False
    try:
        exp, sig = request.cookies.get(COOKIE, "").split(".", 1)
        return int(exp) > time.time() and hmac.compare_digest(sig, _sign(cfg, exp))
    except (ValueError, AttributeError):
        return False


def host_ok(host):
    """Solo localhost, *.local o IPs de red local: evita que una web externa apunte su nombre a tu PC."""
    h = host.lower()
    h = h.split("]")[0] + "]" if h.startswith("[") else h.rsplit(":", 1)[0]
    if h in ("localhost", "[::1]") or h.endswith(".local") or h.endswith(".ts.net"):
        return True
    return bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+", h) and _PRIVATE.match(h))


def lock_wait(ip):
    e = _fails.get(ip)
    return max(0, int(e["until"] - time.time())) if e else 0


@app.before_request
def guard():
    if not host_ok(request.host):
        abort(403)
    # Las órdenes solo se aceptan como JSON de verdad: una web externa no puede enviarlo sin permiso del navegador
    if request.method == "POST" and request.mimetype != "application/json":
        abort(415)
    cfg = pin_cfg()
    if cfg is None or is_loopback():
        return None
    p = request.path
    # públicas: la pantalla del PIN necesita sus iconos y su diccionario de textos
    if p in ("/", "/api/login", "/manifest.webmanifest", "/static/i18n.js") or p.startswith("/static/icon-"):
        return None
    if authed(cfg):
        return None
    if p.startswith("/api/"):
        return jsonify(code="auth", error="PIN required"), 401
    abort(401)


@app.route("/api/login", methods=["POST"])
def api_login():
    cfg = pin_cfg()
    if cfg is None or is_loopback():
        return jsonify(ok=True)
    if cfg.get("invalid"):
        return jsonify(code="broken", error="The PIN file is damaged: run setup-pin.bat again"), 500
    ip = request.remote_addr
    wait = lock_wait(ip)
    if wait:
        return jsonify(code="locked", error="Too many attempts", wait=wait), 429
    pin = str((request.get_json(force=True) or {}).get("pin", ""))[:64]
    digest = hashlib.scrypt(pin.encode(), salt=cfg["_salt"], n=2 ** 14, r=8, p=1, dklen=32)
    if hmac.compare_digest(digest, cfg["_hash"]):
        _fails.pop(ip, None)
        resp = jsonify(ok=True)
        set_auth_cookie(resp, cfg)
        return resp
    e = _fails.setdefault(ip, {"n": 0, "until": 0.0, "strikes": 0})
    e["n"] += 1
    if e["n"] >= MAX_FAILS:                # 5 fallos: 5 min; si insiste, el doble cada vez (máx. 1 h)
        e["strikes"] += 1
        e["n"] = 0
        e["until"] = time.time() + min(3600, 300 * 2 ** (e["strikes"] - 1))
    return jsonify(code="bad_pin", error="Wrong PIN", wait=lock_wait(ip), left=MAX_FAILS - e["n"]), 401


@app.route("/api/auth")
def api_auth():
    return jsonify(ok=True)


# ──────────────────── Web (PWA) ────────────────────
@app.route("/")
def index():
    cfg = pin_cfg()
    if cfg is not None and not authed(cfg):
        resp = send_from_directory(STATIC, "login.html")      # pantalla del PIN
    else:
        resp = send_from_directory(STATIC, "index.html")
        if cfg is not None and not cfg.get("invalid") and not is_loopback():
            set_auth_cookie(resp, cfg)                        # cada visita renueva los 90 días
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(STATIC, "manifest.webmanifest", mimetype="application/manifest+json")


@app.route("/static/<path:p>")
def static_files(p):
    resp = send_from_directory(STATIC, p)
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


# ──────────────── Red: mixer.local ────────────────
def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def advertise():
    """Anuncia mixer.local en la red actual y se reajusta si cambias de WiFi/IP."""
    from zeroconf import ServiceInfo, Zeroconf

    zc, current = None, None
    while True:
        ip = local_ip()
        if ip != current:
            try:
                if zc:
                    zc.unregister_all_services()
                    zc.close()
                zc = Zeroconf()
                zc.register_service(
                    ServiceInfo("_http._tcp.local.", "Mixer remoto._http._tcp.local.",
                                addresses=[socket.inet_aton(ip)], port=PORT,
                                server=f"{HOSTNAME}.local."),
                    allow_name_change=True,
                )
                current = ip
                print(tr(f"  Anunciado como http://{HOSTNAME}.local:{PORT}  ({ip})",
                         f"  Announced as http://{HOSTNAME}.local:{PORT}  ({ip})"))
            except Exception as e:
                print("  mDNS:", e)
                current = None
        time.sleep(10)


if __name__ == "__main__":
    from waitress import serve

    print(tr(f"\n  En el móvil abre:  http://{HOSTNAME}.local:{PORT}", f"\n  Open on your phone:  http://{HOSTNAME}.local:{PORT}"))
    print(tr(f"  (o por IP:         http://{local_ip()}:{PORT})\n", f"  (or by IP:           http://{local_ip()}:{PORT})\n"))
    threading.Thread(target=engine, daemon=True).start()
    threading.Thread(target=duck_loop, daemon=True).start()
    discord_rpc.on_change = wake.set
    threading.Thread(target=discord_rpc.run, daemon=True).start()
    threading.Thread(target=advertise, daemon=True).start()
    if MediaManager:
        threading.Thread(target=media_thread, daemon=True).start()
    serve(app, host="0.0.0.0", port=PORT, threads=64, ident="mixer")
