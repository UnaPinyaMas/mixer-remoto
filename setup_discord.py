"""Guarda los dos códigos de tu aplicación de Discord (los escribes tú, aquí, en tu PC).

EN: Stores the two codes of your Discord application (you type them yourself, here, on your PC).
"""
import sys

import discord_rpc
from mixer_i18n import tr

print()
print(tr("  Configurar Discord para el Mixer", "  Set up Discord for the Mixer"))
print("  --------------------------------")
print(tr("  Los códigos se guardan SOLO en este PC (discord_rpc.json) y únicamente se envían a Discord.",
         "  The codes are stored ONLY on this PC (discord_rpc.json) and are only ever sent to Discord."))
print(tr("  Si no sabes dónde están, mira la guía: docs/discord.es.md",
         "  If you don't know where to find them, see the guide: docs/discord.en.md"))
print()

cfg = discord_rpc.load_cfg()
cid = input(tr("  1) ID de la aplicación (Application ID): ", "  1) Application ID: ")).strip()
secret = input(tr("  2) Secreto del cliente (Client Secret): ", "  2) Client Secret: ")).strip()
if not cid.isdigit() or len(cid) < 15:
    print(tr("\n  El ID de aplicación son solo números (unos 18 dígitos). Revísalo y vuelve a probar.",
             "\n  The Application ID is numbers only (about 18 digits). Check it and try again."))
    sys.exit(1)
if len(secret) < 20:
    print(tr("\n  El secreto parece demasiado corto. Cópialo entero desde el portal de Discord.",
             "\n  The secret looks too short. Copy it in full from the Discord portal."))
    sys.exit(1)

# si cambian los códigos, el permiso anterior ya no vale
cfg.update(client_id=cid, client_secret=secret)
for k in ("access_token", "refresh_token", "expires_at"):
    cfg.pop(k, None)
discord_rpc.save_cfg(cfg)

print(tr("\n  Listo. En unos segundos Discord mostrará una ventana pidiendo permiso: pulsa «Autorizar».",
         "\n  Done. In a few seconds Discord will show a window asking for permission: click “Authorize”."))
print(tr("  (Discord debe estar abierto y el Mixer en marcha.)\n", "  (Discord must be open and the Mixer running.)\n"))
