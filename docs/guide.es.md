# Guía rápida

🇬🇧 [English](guide.en.md) · 🇪🇸 Español · [← Volver al README](../README.es.md)

## Cómo entrar

| Desde | Dirección |
|---|---|
| Móvil (misma WiFi que el PC) | `http://mixer.local:8080` |
| Si esa no abre | `http://192.168.x.x:8080` (la IP de tu PC; al arrancar, el servidor la escribe) |
| El propio PC | `http://localhost:8080` (no pide PIN) |

## PIN

- **Crear o cambiar:** doble clic en `setup-pin.bat`.
- **Quitarlo:** el mismo script, dejando el PIN vacío.
- Cada dispositivo lo pide **una vez** y lo recuerda 90 días (se renueva cada vez que entras).
- Tras 5 fallos seguidos desde un mismo dispositivo se bloquea 5 minutos (y el doble si insiste).
- Si cambias el PIN, todos los dispositivos tienen que volver a introducirlo.

## Arranque

- Arranca solo al iniciar sesión en Windows (acceso directo `MixerRemoto` en la carpeta de Inicio).
- Un vigilante (`supervisor.py`) lo reinicia si se cae o se cuelga. Registros: `supervisor.log` y `server.log`.
- **Instalar o reparar** el arranque automático: `install-autostart.bat`.
- **Arrancarlo a mano** (con ventana, para ver mensajes): `start.bat`.

## Discord (bajar la música cuando alguien habla)

Configuración paso a paso: [discord.es.md](discord.es.md) (`setup-discord.bat`). Registro de la conexión: `rpc.log`.

## Idioma

La interfaz usa el idioma de tu navegador y tiene un botón **ES · EN** abajo del todo. Los mensajes de consola y los registros usan el idioma de Windows; se puede forzar con la variable de entorno `MIXER_LANG=es` o `MIXER_LANG=en`.

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| «Reconectando…» en el móvil | El PC está apagado o en reposo, o el Mixer no está en marcha. |
| «No hay ninguna salida de audio activa» | Enciende los auriculares o conecta unos altavoces. |
| Pide el PIN otra vez | Se borraron los datos del navegador, pasaron 90 días o se cambió el PIN. |

## Archivos que no debes compartir

`pin.json` (huella del PIN) y `discord_rpc.json` (códigos de tu aplicación de Discord). Están en el `.gitignore`.
