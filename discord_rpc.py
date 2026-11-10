"""Conexión local con Discord (RPC) para saber QUIÉN HABLA, sin mirar el volumen.

Discord escucha en una tubería local (\\\\.\\pipe\\discord-ipc-N). Con una aplicación de desarrollador propia
(gratis) y un permiso que se acepta una vez en Discord, avisa de SPEAKING_START / SPEAKING_STOP.
Nada sale del PC salvo el canje del permiso con discord.com.

EN: local connection to Discord (RPC) to know WHO IS TALKING without looking at volume levels.
Discord listens on a local pipe. With your own (free) developer application and a permission you accept once
in Discord, it reports SPEAKING_START / SPEAKING_STOP. Nothing leaves the PC except the token exchange with discord.com.
"""
import ctypes
import json
import msvcrt
import os
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from mixer_i18n import tr

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "discord_rpc.json")
REDIRECT = "http://localhost"
SCOPES = ["rpc", "rpc.voice.read"]
UA = "DiscordBot (mixer-remoto, 1.0)"
HEARTBEAT_S = 3.0      # cada cuánto se comprueba en qué canal de voz estás

# "code" y "detail" los traduce la web; "status" es el mismo texto ya traducido, para registros y otros usos
state = {"configured": False, "connected": False, "channel": False, "channel_name": "", "speaking": 0,
         "code": "unconfigured", "detail": "", "status": ""}
STATUS = {
    "unconfigured": ("Sin configurar: ejecuta setup-discord.bat", "Not set up: run setup-discord.bat"),
    "connecting": ("Conectando con Discord…", "Connecting to Discord…"),
    "authorize": ("Acepta el permiso en la ventana de Discord…", "Accept the permission in the Discord window…"),
    "connected": ("Conectado a Discord", "Connected to Discord"),
    "error": ("Sin conexión con Discord: {detail}", "Can't reach Discord: {detail}"),
}
LOG = os.path.join(BASE, "rpc.log")


def log(msg):
    """Registro pequeño de lo que pasa (cambios de canal, errores) para poder diagnosticar."""
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 100_000:
            os.replace(LOG, LOG + ".old")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except OSError:
        pass
on_change = lambda: None          # el servidor lo sustituye para refrescar la interfaz
_speaking = set()
_self_id = None


def set_status(code, detail=""):
    _set(code=code, detail=detail, status=tr(*STATUS[code]).format(detail=detail))


def _set(**kw):
    changed = any(state.get(k) != v for k, v in kw.items())
    state.update(kw)
    if changed:
        try:
            on_change()
        except Exception:
            pass


def load_cfg():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1)
    os.replace(tmp, CONFIG)


class Pipe:
    def __init__(self):
        self._lock = threading.Lock()
        last = None
        for n in range(10):
            try:
                self.f = open(rf"\\?\pipe\discord-ipc-{n}", "r+b", buffering=0)
                return
            except OSError as e:
                last = e
        raise ConnectionError(tr("Discord no está abierto", "Discord isn't open")) from last

    def send(self, op, payload):
        data = json.dumps(payload).encode()
        with self._lock:                      # lo usan el hilo principal y el de revisión periódica
            self.f.write(struct.pack("<II", op, len(data)) + data)

    def _available(self):
        """Bytes listos para leer. Se mira antes de leer porque en Windows una lectura bloqueante
        impediría escribir (y por tanto revisar el canal) hasta que llegara algún mensaje."""
        avail = ctypes.c_ulong(0)
        ok = ctypes.windll.kernel32.PeekNamedPipe(
            ctypes.c_void_p(msvcrt.get_osfhandle(self.f.fileno())), None, 0, None, ctypes.byref(avail), None)
        if not ok:
            raise EOFError(tr("Discord cerró la conexión", "Discord closed the connection"))
        return avail.value

    def _read(self, n, idle=None):
        buf = b""
        while len(buf) < n:
            avail = self._available()
            if not avail:
                if idle:
                    idle()
                time.sleep(0.03)
                continue
            chunk = self.f.read(min(avail, n - len(buf)))
            if not chunk:
                raise EOFError(tr("Discord cerró la conexión", "Discord closed the connection"))
            buf += chunk
        return buf

    def recv(self, idle=None):
        op, length = struct.unpack("<II", self._read(8, idle))
        return op, json.loads(self._read(length, idle) if length else b"{}")

    def close(self):
        try:
            self.f.close()
        except Exception:
            pass


def _token_request(cfg, form):
    form = dict(form, client_id=cfg["client_id"], client_secret=cfg["client_secret"], redirect_uri=REDIRECT)
    req = urllib.request.Request("https://discord.com/api/oauth2/token", urllib.parse.urlencode(form).encode(),
                                 {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r)
    cfg["access_token"] = d["access_token"]
    cfg["refresh_token"] = d.get("refresh_token", cfg.get("refresh_token"))
    cfg["expires_at"] = time.time() + int(d.get("expires_in", 604800))
    save_cfg(cfg)


class Session:
    def __init__(self, cfg):
        self.cfg = cfg
        self.pipe = Pipe()
        self.pending_channel = None      # (True, id) cuando Discord avisa de un cambio de canal de voz
        self.channel = None
        self.alive = False
        self._hb_t = 0.0

    # ---- comunicación ----
    def _frame(self, op, msg):
        if op == 3:                                     # PING -> PONG
            self.pipe.send(4, msg)
        elif op == 2:
            raise EOFError(tr("Discord cerró la conexión", "Discord closed the connection"))
        elif msg.get("evt") and msg.get("cmd") == "DISPATCH":
            self._event(msg)
        elif str(msg.get("nonce", "")).startswith("hb-") and msg.get("cmd") == "GET_SELECTED_VOICE_CHANNEL":
            # respuesta de la revisión periódica: si Discord dice otro canal, hay que cambiar
            cid = (msg.get("data") or {}).get("id")
            if cid != self.channel:
                log(tr(f"revisión periódica: Discord dice canal {cid}, yo escuchaba {self.channel}",
                       f"periodic check: Discord says channel {cid}, I was listening to {self.channel}"))
                self.pending_channel = (True, cid)

    def cmd(self, name, args=None, evt=None):
        nonce = str(uuid.uuid4())
        msg = {"cmd": name, "args": args or {}, "nonce": nonce}
        if evt:
            msg["evt"] = evt
        self.pipe.send(1, msg)
        while True:
            op, resp = self._recv()
            if resp.get("nonce") == nonce:
                if resp.get("evt") == "ERROR":
                    d = resp.get("data") or {}
                    raise RuntimeError(f"{d.get('message', 'error')} ({tr('código', 'code')} {d.get('code')})")
                return resp
            self._frame(op, resp)

    def _event(self, msg):
        global _self_id
        evt, d = msg.get("evt"), msg.get("data") or {}
        if evt == "VOICE_CHANNEL_SELECT":
            log(tr(f"aviso de Discord: cambio de canal -> {d.get('channel_id')}",
                   f"Discord notice: channel change -> {d.get('channel_id')}"))
            self.pending_channel = (True, d.get("channel_id"))
        elif evt == "SPEAKING_START" and d.get("user_id") != _self_id:
            _speaking.add(d.get("user_id")); _set(speaking=len(_speaking))
        elif evt == "SPEAKING_STOP":
            _speaking.discard(d.get("user_id")); _set(speaking=len(_speaking))

    # ---- pasos ----
    def handshake(self):
        self.pipe.send(0, {"v": 1, "client_id": self.cfg["client_id"]})
        op, resp = self._recv()
        if op == 2 or resp.get("evt") == "ERROR" or resp.get("code"):
            raise RuntimeError(resp.get("message") or tr("Discord rechazó el ID de aplicación", "Discord rejected the application ID"))

    def authenticate(self):
        global _self_id
        cfg = self.cfg
        token = cfg.get("access_token")
        if token and cfg.get("expires_at", 0) < time.time() + 120:
            token = None
            if cfg.get("refresh_token"):
                try:
                    _token_request(cfg, {"grant_type": "refresh_token", "refresh_token": cfg["refresh_token"]})
                    token = cfg["access_token"]
                except Exception:
                    token = None
        if token:
            try:
                resp = self.cmd("AUTHENTICATE", {"access_token": token})
                _self_id = resp["data"]["user"]["id"]
                return
            except RuntimeError:
                cfg.pop("access_token", None)
        # permiso nuevo: Discord enseña una ventana para aceptar (solo la primera vez)
        set_status("authorize")
        resp = self.cmd("AUTHORIZE", {"client_id": cfg["client_id"], "scopes": SCOPES})
        _token_request(cfg, {"grant_type": "authorization_code", "code": resp["data"]["code"]})
        resp = self.cmd("AUTHENTICATE", {"access_token": cfg["access_token"]})
        _self_id = resp["data"]["user"]["id"]

    def current_channel(self):
        """Pregunta a Discord en qué canal de voz estás (es la fuente de verdad)."""
        d = self.cmd("GET_SELECTED_VOICE_CHANNEL").get("data") or {}
        return d.get("id"), d.get("name") or ""

    def set_channel(self, ch, name=""):
        if ch and ch == self.channel:
            return
        if self.channel:
            for evt in ("SPEAKING_START", "SPEAKING_STOP"):
                try:
                    self.cmd("UNSUBSCRIBE", {"channel_id": self.channel}, evt)
                except Exception as e:
                    log(tr(f"no se pudo dejar de escuchar el canal anterior ({evt}): {e}",
                           f"couldn't stop listening to the previous channel ({evt}): {e}"))
        self.channel = None
        _speaking.clear()
        _set(channel=False, channel_name="", speaking=0)
        if ch:
            for evt in ("SPEAKING_START", "SPEAKING_STOP"):
                self.cmd("SUBSCRIBE", {"channel_id": ch}, evt)
        self.channel = ch
        log(tr(f"escuchando el canal {ch} ({name})", f"listening to channel {ch} ({name})") if ch
            else tr("sin canal de voz", "no voice channel"))
        _set(channel=bool(ch), channel_name=name, speaking=0)

    def _recv(self):
        return self.pipe.recv(self._idle)

    def _idle(self):
        """Se ejecuta mientras se espera a Discord: cada 3 s pregunta en qué canal estás, porque Discord
        no siempre avisa de los cambios. (Se hace en el mismo hilo que lee: así no se bloquean entre sí.)"""
        now = time.time()
        if self.alive and now - self._hb_t >= HEARTBEAT_S:
            self._hb_t = now
            self.pipe.send(1, {"cmd": "GET_SELECTED_VOICE_CHANNEL", "args": {}, "nonce": "hb-" + uuid.uuid4().hex})

    def run(self):
        self.handshake()
        set_status("connecting")
        self.authenticate()
        _set(connected=True)
        set_status("connected")
        self.cmd("SUBSCRIBE", {}, "VOICE_CHANNEL_SELECT")
        self.alive = True
        self._hb_t = time.time()
        self.set_channel(*self.current_channel())
        while True:
            op, msg = self._recv()
            self._frame(op, msg)
            if self.pending_channel:
                self.pending_channel = None
                self.set_channel(*self.current_channel())   # no me fío del aviso: pregunto el canal real

    def close(self):
        self.alive = False
        self.pipe.close()


def run():
    """Bucle permanente (en un hilo): se conecta, y si Discord se cierra o falla, reintenta."""
    while True:
        cfg = load_cfg()
        if not cfg.get("client_id") or not cfg.get("client_secret"):
            _set(configured=False, connected=False, channel=False, speaking=0)
            set_status("unconfigured")
            time.sleep(5)
            continue
        _set(configured=True)
        sess = None
        try:
            sess = Session(cfg)
            sess.run()
        except Exception as e:
            log(tr(f"conexión perdida: {e}", f"connection lost: {e}"))
            _speaking.clear()
            _set(connected=False, channel=False, channel_name="", speaking=0)
            set_status("error", str(e))
        finally:
            if sess:
                sess.close()
        time.sleep(5)
