"""Idioma de los mensajes de consola y registros · Language for console messages and logs.

Usa el idioma de Windows (español si el sistema está en español, inglés en el resto).
Se puede forzar con la variable de entorno  MIXER_LANG=es  o  MIXER_LANG=en.

Uses the Windows display language (Spanish on a Spanish system, English otherwise).
Force it with the environment variable  MIXER_LANG=es  or  MIXER_LANG=en.

    from mixer_i18n import tr
    print(tr("Hola", "Hello"))
"""
import ctypes
import locale
import os


def _detect():
    forced = os.environ.get("MIXER_LANG", "").strip().lower()[:2]
    if forced in ("es", "en"):
        return forced
    try:
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()   # LANGID: 0x0A = español (cualquier variante)
        return "es" if (lang_id & 0x3FF) == 0x0A else "en"
    except Exception:
        loc = (locale.getlocale()[0] or "").lower()
        return "es" if loc.startswith(("es", "spanish")) else "en"


LANG = _detect()


def tr(es, en):
    """Devuelve el texto en español o en inglés según el idioma activo."""
    return es if LANG == "es" else en
