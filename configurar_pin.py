"""Crea, cambia o quita el PIN del Mixer. El PIN se escribe aquí, en el PC; no se guarda tal cual, solo su huella."""
import getpass
import hashlib
import json
import os
import secrets
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PIN_FILE = os.path.join(BASE, "pin.json")

print()
print("  PIN del Mixer")
print("  -------------")
print("  Cada dispositivo (iPhone, otro ordenador...) lo pedirá UNA vez y lo recordará 90 días.")
print("  Para QUITAR el PIN, deja la casilla vacía y pulsa Enter.")
print("  (Mientras escribes no se ve nada: es normal.)")
print()

pin = getpass.getpass("  Nuevo PIN (4 a 8 cifras): ").strip()

if not pin:
    if os.path.exists(PIN_FILE):
        os.remove(PIN_FILE)
        print("\n  PIN quitado. El Mixer vuelve a abrirse sin pedir nada.\n")
    else:
        print("\n  No había ningún PIN. No se ha cambiado nada.\n")
    sys.exit(0)

if not (pin.isdigit() and 4 <= len(pin) <= 8):
    print("\n  El PIN debe tener entre 4 y 8 cifras (solo números). Vuelve a ejecutarlo.\n")
    sys.exit(1)
if getpass.getpass("  Repítelo: ").strip() != pin:
    print("\n  No coinciden. No se ha cambiado nada.\n")
    sys.exit(1)

salt = secrets.token_bytes(16)
digest = hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
cfg = {"salt": salt.hex(), "hash": digest.hex(), "secret": secrets.token_bytes(32).hex()}
tmp = PIN_FILE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cfg, f)
os.replace(tmp, PIN_FILE)

print("\n  Listo. El PIN ya está activo (no hace falta reiniciar nada).")
print("  Los dispositivos que ya tenían acceso tendrán que introducirlo de nuevo, una vez.")
print("  Desde este mismo PC, usando http://localhost:8080, no se pide.\n")
