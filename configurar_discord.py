"""Guarda los dos códigos de tu aplicación de Discord (los escribes tú, aquí, en tu PC)."""
import os
import sys

import discord_rpc

print()
print("  Configurar Discord para el Mixer")
print("  --------------------------------")
print("  Los códigos se guardan SOLO en este PC (discord_rpc.json) y únicamente se envían a Discord.")
print("  Si no sabes dónde están, mira el archivo LEEME-DISCORD.txt.")
print()

cfg = discord_rpc.load_cfg()
cid = input("  1) ID de la aplicación (Application ID): ").strip()
secret = input("  2) Secreto del cliente (Client Secret): ").strip()
if not cid.isdigit() or len(cid) < 15:
    print("\n  El ID de aplicación son solo números (unos 18 dígitos). Revísalo y vuelve a probar.")
    sys.exit(1)
if len(secret) < 20:
    print("\n  El secreto parece demasiado corto. Cópialo entero desde el portal de Discord.")
    sys.exit(1)

# si cambian los códigos, el permiso anterior ya no vale
cfg.update(client_id=cid, client_secret=secret)
for k in ("access_token", "refresh_token", "expires_at"):
    cfg.pop(k, None)
discord_rpc.save_cfg(cfg)

print("\n  Listo. En unos segundos Discord mostrará una ventana pidiendo permiso: pulsa «Autorizar».")
print("  (Discord debe estar abierto y el Mixer en marcha.)\n")
