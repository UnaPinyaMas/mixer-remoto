# Detectar quién habla en Discord

🇬🇧 [English](discord.en.md) · 🇪🇸 Español · [← Volver al README](../README.es.md)

Para que **«Bajar música al hablar»** funcione de verdad (sin confundirse con música ni avisos), el Mixer necesita saber quién habla en tu canal de voz. Discord lo permite con una aplicación de desarrollador **gratuita** y un permiso que se acepta una sola vez. Necesitas **Discord de escritorio** abierto en el PC.

## Pasos

1. **Crea una aplicación en Discord.** Entra en <https://discord.com/developers/applications> con tu cuenta, pulsa *New Application*, ponle de nombre «Mixer» y acepta.

2. **Añade la dirección de redirección.** En el menú de la izquierda, **OAuth2**. En *Redirects* pulsa *Add Redirect* y escribe exactamente `http://localhost`. Pulsa *Save Changes*.

3. **Copia los dos códigos.**
   - **Application ID:** en *General Information* (es un número largo).
   - **Client Secret:** en *OAuth2* → *Client Secret* → *Reset Secret*, y copia el texto. Solo se muestra una vez; si lo pierdes, vuelve a resetearlo. **Es como una contraseña: no lo compartas.**

4. **Dáselos al Mixer.** Doble clic en `setup-discord.bat`. Pega el Application ID (Enter) y el Client Secret (Enter).

5. **Acepta el permiso.** En unos segundos Discord enseñará una ventana: «Mixer quiere acceder a tu cuenta». Pulsa **Autorizar**. Solo se pide la primera vez.

Listo: bajo «Bajar música al hablar», el Mixer mostrará el nombre de tu canal de voz y quién habla.

## Si algo falla

El motivo sale escrito en esa misma zona de la pantalla del Mixer. También puedes mirar `rpc.log`.

## Quitarlo todo

Borra el archivo `discord_rpc.json` y, en el portal, la aplicación «Mixer».

> La conexión local con Discord (RPC) es una función restringida de Discord: funciona con una aplicación tuya y tu propia cuenta, pero Discord puede cambiarla.
