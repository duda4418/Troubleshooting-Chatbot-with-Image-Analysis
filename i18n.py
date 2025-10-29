# i18n.py
import gettext
import os

SUPPORTED = {"en", "ro", "de"}
DEFAULT_LANG = "en"

def set_locale(lang: str | None):
    lang = (lang or DEFAULT_LANG).lower()
    if lang not in SUPPORTED:
        lang = DEFAULT_LANG
    locales_dir = os.path.join(os.path.dirname(__file__), "locales")
    trans = gettext.translation(
        domain="messages",
        localedir=locales_dir,
        languages=[lang],
        fallback=True
    )
    trans.install()
    return lang
