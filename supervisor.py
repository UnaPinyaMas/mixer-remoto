"""Vigilante del Mixer: arranca el servidor y lo relanza si se cae o se queda colgado."""
import datetime
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import psutil

BASE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(BASE, "server.py")
PORT = int(os.environ.get("MIXER_PORT", 8080))
LOCK_PORT = 48080          # solo para evitar dos vigilantes a la vez
CREATE_NO_WINDOW = 0x08000000


def log(msg):
    path = os.path.join(BASE, "supervisor.log")
    try:
        if os.path.exists(path) and os.path.getsize(path) > 256_000:
            os.replace(path, path + ".old")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
    except OSError:
        pass


def kill_stale():
    """Cierra servidores del Mixer que hayan quedado sueltos (el puerto estaría ocupado)."""
    me = os.getpid()
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
            if p.info["pid"] != me and any(c.lower().endswith("server.py") for c in cmd) \
                    and os.path.abspath(cmd[-1]) == SERVER:
                p.kill()
        except (psutil.Error, OSError):
            pass


def start():
    out = open(os.path.join(BASE, "server.log"), "ab")
    return subprocess.Popen([sys.executable, SERVER], cwd=BASE, stdout=out, stderr=out,
                            creationflags=CREATE_NO_WINDOW)


def healthy():
    """Vivo = contesta, aunque sea con un error. Solo se reinicia si no contesta (colgado) o está caído:
    reiniciar no arregla un error del programa, y antes provocaba reinicios sin fin si no había audio."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/state", timeout=6):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def main():
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        return  # ya hay un vigilante funcionando

    kill_stale()
    time.sleep(1)
    child, started, fails = start(), time.time(), 0
    log("vigilante iniciado; servidor arrancado")
    while True:
        time.sleep(5)
        if child.poll() is not None:
            quick = time.time() - started < 20      # si se cae nada más arrancar, espera más
            log(f"el servidor se cerró (código {child.returncode}); reinicio")
            time.sleep(8 if quick else 2)
            kill_stale()
            child, started, fails = start(), time.time(), 0
            continue
        if time.time() - started < 20:
            continue                                # margen para que termine de arrancar
        if healthy():
            fails = 0
        else:
            fails += 1
            if fails >= 3:                          # ~15 s sin responder: colgado
                log("el servidor no responde; reinicio")
                child.kill()
                child.wait()
                kill_stale()
                child, started, fails = start(), time.time(), 0


if __name__ == "__main__":
    main()
