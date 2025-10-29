import os
import json
import requests
import streamlit as st
from i18n import set_locale  # instalează gettext "_" global și returnează codul efectiv

# --- Config pagină
st.set_page_config(page_title="Dishwasher Troubleshooting Assistant", layout="wide")
st.title("🧼 Dishwasher Troubleshooting Assistant")

API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- State init
def init_state():
    defaults = {
        "session_id": None,
        "label": None,
        "confidence": None,
        "phase": None,
        "chat_history": [],
        "quick_replies": [],
        "debug": False,
        "last_resp": None,
        "api_logs": [],
        "lang": "en",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

init_state()

# ✅ Instalează '_' înainte de orice folosire
lang = set_locale(st.session_state["lang"])
try:
    _
except NameError:
    _ = lambda s: s  # fallback dacă set_locale nu a înregistrat _

# --- Helpers i18n
def translate_quick_replies(qrs):
    """Returnează (lista_etichete_traduse, mapare inversă etichetă_tradusă -> original)."""
    mapping = {
        "Yes": _("Yes"),
        "No": _("No"),
        "Solved": _("Solved"),
        "Not solved": _("Not solved"),
        "More options": _("More options"),
        "Try again": _("Try again"),
        "Send feedback": _("Send feedback"),
        "Start": _("Start"),
    }
    translated = [mapping.get(x, x) for x in qrs]
    reverse = {mapping.get(x, x): x for x in qrs}
    return translated, reverse

# Badge culori faze
PHASE_COLORS = {
    "analyzed": "#0d6efd",
    "intro": "#6f42c1",
    "steps": "#198754",
    "alternatives": "#fd7e14",
    "end": "#dc3545",
}

# Map evenimente (rămân ENG)
EVENT_MAP = {
    "Yes": "confirm",
    "No": "done",
    "Solved": "solved",
    "Not solved": "not_solved",
    "More options": "not_solved",
    "Try again": "try_again",
    "Start": "start",
    "Send feedback": "done",
}

# --- Sidebar: limbă + info
with st.sidebar:
    st.subheader(_("Language / Limba / Sprache"))
    st.session_state["lang"] = st.selectbox(
        _("Choose language"),
        options=["en", "ro", "de"],
        index=["en", "ro", "de"].index(st.session_state["lang"])
    )

# Reinstalează locale dacă userul a schimbat limba
lang = set_locale(st.session_state["lang"])

def push_assistant(msg: str):
    st.session_state.chat_history.append(("assistant", msg))

def push_user(msg: str):
    st.session_state.chat_history.append(("you", msg))

def render_actions(actions):
    if not actions:
        return
    st.markdown("**" + _("Actions / Steps:") + "**")
    for a in actions:
        if isinstance(a, dict):
            st.markdown(f"- `{a.get('type')}` • `{a.get('target')}` → `{a.get('value')}`")
        else:
            st.markdown(f"- {a}")

def call_analyze(image_file, notes):
    import time
    start_ts = time.time()
    files = {"image": (image_file.name, image_file.getvalue(), image_file.type)}
    data = {"user_text": notes}
    url = f"{API_URL}/analyze"
    resp = requests.post(url, files=files, data=data, params={"lang": lang})
    elapsed = (time.time() - start_ts) * 1000
    if resp.status_code == 200:
        js = resp.json()
        st.session_state.session_id = js["session_id"]
        st.session_state.label = js["label"]
        st.session_state.confidence = js["confidence"]
        st.session_state.chat_history = []
        st.session_state.quick_replies = []
        st.session_state.phase = "analyzed"
        st.success(_("Identified: {label} (confidence {conf:.2f})").format(
            label=js["label"], conf=js["confidence"]
        ))
        st.session_state.api_logs.append({
            "endpoint": "/analyze",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "payload_summary": {"notes_len": len(notes or ""), "filename": image_file.name},
        })
    else:
        st.error(_("Analyze error: {text}").format(text=resp.text))
        st.session_state.api_logs.append({
            "endpoint": "/analyze",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "error": resp.text[:200],
        })

def call_chat(event: str, user_input: str = ""):
    import time
    start_ts = time.time()
    payload = {"session_id": st.session_state.session_id, "event": event, "user_input": user_input}
    url = f"{API_URL}/chat"
    resp = requests.post(url, json=payload, params={"lang": lang})
    elapsed = (time.time() - start_ts) * 1000
    if resp.status_code == 200:
        js = resp.json()
        st.session_state.api_logs.append({
            "endpoint": "/chat",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "payload_summary": {"event": event, "has_user_input": bool(user_input)},
            "reply_keys": list(js.keys()),
        })
        return js
    st.error(_("Chat error: {text}").format(text=resp.text))
    st.session_state.api_logs.append({
        "endpoint": "/chat",
        "method": "POST",
        "status": resp.status_code,
        "elapsed_ms": round(elapsed, 1),
        "error": resp.text[:200],
        "payload_summary": {"event": event},
    })
    return None

def reset_session():
    for k in ["session_id", "label", "confidence", "phase", "chat_history", "quick_replies", "last_resp"]:
        st.session_state.pop(k, None)
    init_state()
    st.success(_("Session reset."))

# --- Sidebar info
with st.sidebar:
    st.subheader(_("Session Info"))
    sid = st.session_state.session_id or "—"
    lbl = st.session_state.label or "—"
    conf = f"{st.session_state.confidence:.2f}" if st.session_state.confidence is not None else "—"
    phs = st.session_state.phase or "—"

    st.write(f"ID: {sid}")
    st.write(f"{_('Label')}: {lbl}")
    st.write(f"{_('Confidence')}: {conf}")
    st.write(f"{_('Phase')}: {phs}")

    st.checkbox("Debug", key="debug")
    if st.button(_("Reset Session")):
        reset_session()

    if st.session_state.debug and st.session_state.last_resp:
        with st.expander(_("Last raw response")):
            st.json(st.session_state.last_resp)
    if st.session_state.debug and st.session_state.get("api_logs"):
        with st.expander(_("API Call Logs")):
            for log in reversed(st.session_state.api_logs[-25:]):
                line = f"{log['method']} {log['endpoint']} → {log['status']} ({log.get('elapsed_ms','?')} ms)"
                st.markdown(f"- {line}")
                if 'payload_summary' in log:
                    st.code(json.dumps(log['payload_summary'], ensure_ascii=False, indent=2), language='json')
                if 'error' in log:
                    st.markdown(f"<span style='color:#dc3545'>{_('Error')}: {log['error']}</span>", unsafe_allow_html=True)

# --- Tabs
tab1, tab2, tab3, tab4 = st.tabs([_("Analyze"), _("Guidance"), _("Feedback"), _("History")])

# --- Tab Analyze
with tab1:
    st.header(_("Analyze Image"))
    img = st.file_uploader(_("Upload result photo"), type=["jpg", "jpeg", "png", "webp"])
    notes = st.text_area(_("Context notes (optional)"))
    if st.button(_("Run Analysis")) and img:
        with st.spinner(_("Analyzing...")):
            call_analyze(img, notes)
    if st.session_state.phase == "analyzed":
        st.info(_("Go to Guidance tab to start troubleshooting."))

# --- Tab Guidance
with tab2:
    st.header(_("Tailored Guidance"))
    if not st.session_state.session_id:
        st.warning(_("Analyze an image first."))
    else:
        # Badge fază curentă
        if st.session_state.phase:
            color = PHASE_COLORS.get(st.session_state.phase, "#6c757d")
            phase_map = {
                "analyzed": _("analyzed"),
                "intro": _("intro"),
                "steps": _("steps"),
                "alternatives": _("alternatives"),
                "end": _("end"),
            }
            phase_label = phase_map.get(st.session_state.phase, st.session_state.phase)
            st.markdown(
                f"<div style='display:inline-block;padding:4px 10px;border-radius:12px;"
                f"background:{color};color:#fff;font-size:12px;margin-bottom:8px;'>"
                f"{_('Phase')}: {phase_label}</div>",
                unsafe_allow_html=True,
            )

        # Start flow
        if len(st.session_state.chat_history) == 0:
            if st.button(_("Start Troubleshooting")):
                js = call_chat("start")
                if js:
                    push_assistant(js["message"])
                    st.session_state.quick_replies = js.get("quick_replies", [])
                    st.session_state.phase = "intro"
                    st.session_state.last_resp = js

        # Conversație existentă (nume localizate)
        name_map = {"assistant": _("assistant"), "you": _("you")}
        for sender, msg in st.session_state.chat_history:
            bubble_bg = "#f8f9fa" if sender == "assistant" else "#e6f7ff"
            align = "left" if sender == "assistant" else "right"
            shown_name = name_map.get(sender, sender)
            st.markdown(
                f"<div style='background:{bubble_bg};padding:8px;border-radius:6px;margin-bottom:4px;text-align:{align}'>"
                f"<b>{shown_name.capitalize()}:</b> {msg}</div>",
                unsafe_allow_html=True,
            )

        # Quick replies
        if st.session_state.quick_replies:
            translated_qr, qr_rev = translate_quick_replies(st.session_state.quick_replies)
            cols = st.columns(len(translated_qr))
            for i, q in enumerate(translated_qr):
                btn_key = f"qr_{i}_{q.replace(' ', '_')}"
                if cols[i].button(q, key=btn_key):
                    orig = qr_rev.get(q, q)
                    event = EVENT_MAP.get(orig, "confirm")
                    js = call_chat(event)
                    if js:
                        push_user(q)
                        push_assistant(js["message"])
                        render_actions(js.get("actions", []))
                        st.session_state.last_resp = js
                        if event == "start":
                            st.session_state.phase = "intro"
                        elif event == "confirm":
                            st.session_state.phase = "steps"
                        elif event in {"not_solved", "try_again"}:
                            st.session_state.phase = "alternatives"
                        elif event in {"solved", "done"}:
                            st.session_state.phase = "end"
                        new_qr = js.get("quick_replies", [])
                        if st.session_state.phase == "steps":
                            new_qr = [x for x in new_qr if x not in {"Yes", "No"}]
                        st.session_state.quick_replies = new_qr
                    break

# --- Tab Feedback
with tab3:
    st.header(_("Feedback"))
    if not st.session_state.session_id:
        st.warning(_("Need an active session."))
    elif st.session_state.phase != "end":
        st.info(_("Finish troubleshooting to enable feedback."))
    else:
        solved = st.radio(_("Problem solved?"), ["Yes", "No"], horizontal=True)
        notes_fb = st.text_area(_("Notes / suggestions"))
        if st.button(_("Submit Feedback")):
            import time
            start_ts = time.time()
            payload = {
                "session_id": st.session_state.session_id,
                "solved": solved == "Yes",
                "final_label": st.session_state.label,
                "notes": notes_fb,
            }
            url = f"{API_URL}/feedback"
            resp = requests.post(url, json=payload, params={"lang": lang})
            elapsed = (time.time() - start_ts) * 1000
            if resp.status_code == 200:
                st.success(_("Thank you for your feedback!"))
            else:
                st.error(_("Feedback error: {text}").format(text=resp.text))

# --- Tab History
with tab4:
    st.header(_("History"))
    if not st.session_state.chat_history:
        st.write(_("No messages yet."))
    else:
        util_cols = st.columns(3)
        if util_cols[0].button(_("Clear History")):
            st.session_state.chat_history = []
            st.session_state.last_resp = None
            st.success(_("History cleared."))

        # Export (nume localizate)
        name_map = {"assistant": _("assistant"), "you": _("you")}
        export_json = json.dumps(
            [{"sender": name_map.get(s, s), "message": m} for s, m in st.session_state.chat_history],
            ensure_ascii=False, indent=2
        )
        md_lines = ["# " + _("Chat History")]
        for s, m in st.session_state.chat_history:
            shown_name = name_map.get(s, s)
            md_lines.append(f"**{shown_name.capitalize()}:** {m}")
        export_md = "\n\n".join(md_lines)

        util_cols[1].download_button(_("Export JSON"), data=export_json,
                                     file_name="chat_history.json", mime="application/json")
        util_cols[2].download_button(_("Export Markdown"), data=export_md,
                                     file_name="chat_history.md", mime="text/markdown")

        for s, m in st.session_state.chat_history:
            shown_name = name_map.get(s, s)
            st.markdown(f"- **{shown_name}:** {m}")

st.caption(_("Fresh UI rebuilt from backend logic. Use sidebar for debug & reset."))