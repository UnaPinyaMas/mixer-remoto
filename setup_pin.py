"""Crea, cambia o quita el PIN del Mixer. El PIN se escribe aquí, en el PC; no se guarda tal cual, solo su huella.

EN: Create, change or remove the Mixer PIN. You type it here on the PC; only a hash of it is stored, never the PIN itself.
"""
import getpass
import hashlib
import json
import os
import secrets
import sys

from mixer_i18n import tr

BASE = os.path.dirname(os.path.abspath(__file__))
PIN_FILE = os.path.join(BASE, "pin.json")

print()
print(tr("  PIN del Mixer", "  Mixer PIN"))
print("  -------------")
print(tr("  Cada dispositivo (móvil, otro ordenador...) lo pedirá UNA vez y lo recordará 90 días.",
         "  Each device (phone, another computer...) will ask for it ONCE and remember it for 90 days."))
print(tr("  Para QUITAR el PIN, deja la casilla vacía y pulsa Enter.",
         "  To REMOVE the PIN, leave it empty and press Enter."))
print(tr("  (Mientras escribes no se ve nada: es normal.)", "  (Nothing shows while you type: that's normal.)"))
print()

pin = getpass.getpass(tr("  Nuevo PIN (4 a 8 cifras): ", "  New PIN (4 to 8 digits): ")).strip()

if not pin:
    if os.path.exists(PIN_FILE):
        os.remove(PIN_FILE)
        print(tr("\n  PIN quitado. El Mixer vuelve a abrirse sin pedir nada.\n",
                 "\n  PIN removed. The Mixer opens without asking again.\n"))
    else:
        print(tr("\n  No había ningún PIN. No se ha cambiado nada.\n", "\n  There was no PIN. Nothing was changed.\n"))
    sys.exit(0)

if not (pin.isdigit() and 4 <= len(pin) <= 8):
    print(tr("\n  El PIN debe tener entre 4 y 8 cifras (solo números). Vuelve a ejecutarlo.\n",
             "\n  The PIN must be 4 to 8 digits (numbers only). Run it again.\n"))
    sys.exit(1)
if getpass.getpass(tr("  Repítelo: ", "  Repeat it: ")).strip() != pin:
    print(tr("\n  No coinciden. No se ha cambiado nada.\n", "\n  They don't match. Nothing was changed.\n"))
    sys.exit(1)

salt = secrets.token_bytes(16)
digest = hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
cfg = {"salt": salt.hex(), "hash": digest.hex(), "secret": secrets.token_bytes(32).hex()}
tmp = PIN_FILE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cfg, f)
os.replace(tmp, PIN_FILE)

print(tr("\n  Listo. El PIN ya está activo (no hace falta reiniciar nada).",
         "\n  Done. The PIN is now active (no restart needed)."))
print(tr("  Los dispositivos que ya tenían acceso tendrán que introducirlo de nuevo, una vez.",
         "  Devices that already had access will have to enter it again, once."))
print(tr("  Desde este mismo PC, usando http://localhost:8080, no se pide.\n",
         "  From this same PC, using http://localhost:8080, it is not asked.\n"))
