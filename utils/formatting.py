# utils/formatting.py
from typing import List, Dict, Union

# Folosim gettext global instalat de i18n.set_locale()
try:
    _
except NameError:  # dacă e importat foarte devreme
    _ = lambda s: s  # no-op; va fi real după set_locale()

def _humanize(token: str) -> str:
    """fallback: inlocuiește _ cu spații, fără a capitaliza agresiv."""
    return (token or "").replace("_", " ")

# Label-uri standard pentru tipuri/targeturi
HEAD_MAP = {
    "request": _("Request"),
    "tip": _("Tip"),
    "guide": _("Guide"),
    "setting": _("Setting"),
    "maintenance": _("Maintenance"),
    "placement": _("Placement"),
}

TARGET_MAP = {
    "capture": _("capture"),
    "lighting": _("lighting"),
    "angle": _("angle"),
    "device": _("device"),
    "rinse_aid": _("rinse aid"),
    "cycle": _("cycle"),
    "spray_arms": _("spray arms"),
}

# Valori comune (poți extinde oricând; cheile sunt tokens din FLOW)
VALUE_MAP = {
    "retake_with_full_rack_visible": _("retake with full rack visible"),
    "use_room_light_no_flash":       _("use room light, no flash"),
    "capture_top_and_bottom_rack":   _("capture top and bottom rack"),
    "include_close_up_of_glass_or_plate": _("include close-up of glass or plate"),
    "upper_rack_front":              _("upper rack, front"),
    "check_and_clean":               _("check and clean"),
    "intensive":                     _("intensive"),
}

def _tr_token(token: str) -> str:
    """Încearcă traducerea prin gettext; dacă nu există, folosește humanize."""
    translated = _(token)
    return translated if translated != token else _humanize(token)

def actions_to_text(actions: List[Union[str, Dict]]) -> str:
    """Transformă lista de acțiuni în text prietenos, cu i18n."""
    if not actions:
        return ""
    lines: List[str] = []
    for a in actions:
        if isinstance(a, dict):
            head   = HEAD_MAP.get(a.get("type", ""), _tr_token(a.get("type", "")))
            target = TARGET_MAP.get(a.get("target", ""), _tr_token(a.get("target", "")))
            value_token = a.get("value", "")
            value  = VALUE_MAP.get(value_token, _tr_token(value_token))
            lines.append(f"• {head} → {target}: {value}")
        else:
            # string simplu
            lines.append(f"• {_tr_token(str(a))}")
    # newline între bullets pentru lizibilitate
    return "\n".join(lines)
