import os  # Modul standard pentru variabile de mediu / path-uri
import json  # Pentru export istoric în format JSON / Markdown
import requests  # Folosit pentru apeluri HTTP către backend (FastAPI)
import streamlit as st  # Biblioteca UI rapidă pentru web apps


# Configurare pagină (titlu browser + layout lat)
st.set_page_config(page_title="Dishwasher Troubleshooting Assistant", layout="wide")
# Titlul principal afișat în aplicație
st.title("🧼 Dishwasher Troubleshooting Assistant")

# URL backend (se poate suprascrie din variabila de mediu API_URL)
API_URL = os.getenv("API_URL", "http://localhost:8000")

def init_state():
    """Initializează cheile din session_state dacă nu există.
    Folosim session_state ca storage client-side pentru a păstra contextul între rerender-uri.
    """
    defaults = {
        "session_id": None,      # ID-ul sesiunii returnat de /analyze (necesar pentru /chat, /feedback)
        "label": None,           # Eticheta (problema) detectată din imagine
        "confidence": None,      # Scorul de încredere pentru eticheta detectată
        "phase": None,           # Faza curentă a fluxului (intro, steps, alternatives, end, analyzed)
        "chat_history": [],      # Listă de tuple (sender, mesaj) pentru a afișa conversația
        "quick_replies": [],     # Lista de butoane rapide venite din backend
        "debug": False,          # Flag UI pentru a afișa răspunsul brut din backend
        "last_resp": None,       # Ultimul JSON brut primit de la /chat (pentru debug persistent)
        "api_logs": [],          # Loguri apeluri HTTP (endpoint, status, durata, sumar payload)
    }
    for k, v in defaults.items():  # Setează valoarea doar dacă cheia nu există încă
        st.session_state.setdefault(k, v)

init_state()

# Dicționar culori pentru badge-ul de fază (vizual rapid progres flux)
PHASE_COLORS = {
    "analyzed": "#0d6efd",      # Albastru inițial după analiză imagine
    "intro": "#6f42c1",          # Mov pentru faza introductivă
    "steps": "#198754",          # Verde când afișăm pașii principali
    "alternatives": "#fd7e14",   # Portocaliu pentru variante alternative / retry
    "end": "#dc3545",            # Roșu la final (închis) / feedback
}

EVENT_MAP = {
    # Mapare text buton -> eveniment backend
    "Yes": "confirm",
    "No": "done",            # Închidere / finalizare fără rezolvare
    "Solved": "solved",       # Utilizator confirmă că problema s-a rezolvat
    "Not solved": "not_solved",  # Cere alternative / nu a mers
    "More options": "not_solved", # Sinomin pentru a cere alternative
    "Try again": "try_again", # Repetare ultim pas / variantă
    "Start": "start",         # Pornire flux ghidare
    "Send feedback": "done",  # Terminare flux (ex. fără alte acțiuni)
}

def push_assistant(msg: str):
    """Adaugă un mesaj de la asistent în istoric."""
    st.session_state.chat_history.append(("assistant", msg))

def push_user(msg: str):
    """Adaugă un mesaj de la utilizator în istoric."""
    st.session_state.chat_history.append(("you", msg))

def render_actions(actions):
    """Afișează lista de acțiuni recomandate (string sau dict structurat)."""
    if not actions:
        return
    st.markdown("**Actions / Steps:**")
    for a in actions:
        if isinstance(a, dict):  # Formă structurată venită din hartă (type/target/value)
            st.markdown(f"- `{a.get('type')}` • `{a.get('target')}` → `{a.get('value')}`")
        else:  # Simpla descriere text
            st.markdown(f"- {a}")

def call_analyze(image_file, notes):
    """Trimite imaginea + note la /analyze și setează contextul sesiunii."""
    import time
    start_ts = time.time()
    files = {"image": (image_file.name, image_file.getvalue(), image_file.type)}  # Multipart pentru fișier
    data = {"user_text": notes}  # Text opțional introdus de utilizator
    url = f"{API_URL}/analyze"
    resp = requests.post(url, files=files, data=data)  # Apel backend
    elapsed = (time.time() - start_ts) * 1000
    if resp.status_code == 200:
        js = resp.json()  # Parsează JSON-ul răspunsului
        # Populatează context sesiune
        st.session_state.session_id = js["session_id"]
        st.session_state.label = js["label"]
        st.session_state.confidence = js["confidence"]
        st.session_state.chat_history = []  # Reset istoric pentru noua problemă
        st.session_state.quick_replies = []
        st.session_state.phase = "analyzed"  # Fază după analiză imagine
        st.success(f"Identified: {js['label']} (confidence {js['confidence']:.2f})")
        st.session_state.api_logs.append({
            "endpoint": "/analyze",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "payload_summary": {"notes_len": len(notes or ""), "filename": image_file.name},
        })
    else:
        st.error(f"Analyze error: {resp.text}")  # Afișează eroare de la server
        st.session_state.api_logs.append({
            "endpoint": "/analyze",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "error": resp.text[:200],
        })

def call_chat(event: str, user_input: str = ""):
    """Trimite un eveniment de flux la /chat și returnează răspunsul JSON."""
    import time
    start_ts = time.time()
    payload = {
        "session_id": st.session_state.session_id,
        "event": event,
        "user_input": user_input,
    }
    url = f"{API_URL}/chat"
    resp = requests.post(url, json=payload)
    elapsed = (time.time() - start_ts) * 1000
    if resp.status_code == 200:
        js = resp.json()
        st.session_state.api_logs.append({
            "endpoint": "/chat",
            "method": "POST",
            "status": resp.status_code,
            "elapsed_ms": round(elapsed, 1),
            "payload_summary": {"event": event, "has_user_input": str(user_input)},
            "reply_keys": list(js.keys()),
        })
        return js
    st.error(f"Chat error: {resp.text}")
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
    """Șterge toate cheile de flux și reinitializează state-ul (hard reset)."""
    for k in ["session_id", "label", "confidence", "phase", "chat_history", "quick_replies"]:
        st.session_state.pop(k, None)  # Elimină dacă există
    init_state()  # Re-creează structura goală
    st.success("Session reset.")

with st.sidebar:  # Bara laterală pentru meta-informații și acțiuni globale
    st.subheader("Session Info")
    st.write(f"ID: {st.session_state.session_id}")  # Afișează ID sesiune dacă există
    st.write(f"Label: {st.session_state.label}")   # Eticheta detectată
    if st.session_state.confidence is not None:
        st.write(f"Confidence: {st.session_state.confidence:.2f}")  # Round scor
    st.write(f"Phase: {st.session_state.phase}")   # Faza fluxului
    st.checkbox("Debug", key="debug")  # Toggle pentru a afișa răspuns brut
    if st.button("Reset Session"):  # Reset hard al întregului context
        reset_session()
    # Afișare persistentă a ultimului răspuns brut din backend dacă debug e activat
    if st.session_state.debug and st.session_state.last_resp:
        with st.expander("Last raw response"):
            st.json(st.session_state.last_resp)
    if st.session_state.debug and st.session_state.get("api_logs"):
        with st.expander("API Call Logs"):
            for log in reversed(st.session_state.api_logs[-25:]):
                line = f"{log['method']} {log['endpoint']} → {log['status']} ({log.get('elapsed_ms','?')} ms)"
                st.markdown(f"- {line}")
                if 'payload_summary' in log:
                    st.code(json.dumps(log['payload_summary'], ensure_ascii=False, indent=2), language='json')
                if 'error' in log:
                    st.markdown(f"<span style='color:#dc3545'>Error: {log['error']}</span>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Analyze", "Guidance", "Feedback", "History"])  # Inițializare tab-uri

with tab1:  # TAB 1 - Analiza imaginii
    st.header("Analyze Image")
    img = st.file_uploader("Upload result photo", type=["jpg", "jpeg", "png", "webp"])  # Upload imagine rezultat
    notes = st.text_area("Context notes (optional)")  # Note opționale user
    if st.button("Run Analysis") and img:  # Start analiză dacă avem imagine
        with st.spinner("Analyzing..."):
            call_analyze(img, notes)
    if st.session_state.phase == "analyzed":  # Indică trecerea la pasul următor
        st.info("Go to Guidance tab to start troubleshooting.")

with tab2:  # TAB 2 - Ghidare personalizată
    st.header("Tailored Guidance")
    if not st.session_state.session_id:  # Nu putem continua fără analiză inițială
        st.warning("Analyze an image first.")
    else:
        # Badge fază curentă (dacă există)
        if st.session_state.phase:
            color = PHASE_COLORS.get(st.session_state.phase, "#6c757d")  # Gri fallback
            st.markdown(
                f"<div style='display:inline-block;padding:4px 10px;border-radius:12px;background:{color};color:#fff;font-size:12px;margin-bottom:8px;'>Phase: {st.session_state.phase}</div>",
                unsafe_allow_html=True,
            )
        if len(st.session_state.chat_history) == 0:  # Dacă fluxul nu a început
            if st.button("Start Troubleshooting"):
                js = call_chat("start")  # Trimite event start
                if js:
                    push_assistant(js["message"])  # Primul mesaj de la asistent
                    st.session_state.quick_replies = js.get("quick_replies", [])
                    st.session_state.phase = "intro"
                    st.session_state.last_resp = js  # Stocăm răspunsul integral pentru debug persistent
        # Afișare conversație existentă
        for sender, msg in st.session_state.chat_history:
            bubble_bg = "#f8f9fa" if sender == "assistant" else "#e6f7ff"  # Culori diferite
            align = "left" if sender == "assistant" else "right"         # Aliniere diferită
            st.markdown(
                f"<div style='background:{bubble_bg};padding:8px;border-radius:6px;margin-bottom:4px;text-align:{align}'><b>{sender.capitalize()}:</b> {msg}</div>",
                unsafe_allow_html=True,
            )
        # Butoane rapide
        if st.session_state.quick_replies:
            # Prevenim dublu-click / rerender inconsistente folosind chei unice
            cols = st.columns(len(st.session_state.quick_replies))
            for i, q in enumerate(st.session_state.quick_replies):
                btn_key = f"qr_{i}_{q.replace(' ', '_')}"
                if cols[i].button(q, key=btn_key):
                    event = EVENT_MAP.get(q, "confirm")
                    js = call_chat(event)
                    if js:
                        push_user(q)
                        push_assistant(js["message"])
                        render_actions(js.get("actions", []))
                        st.session_state.last_resp = js
                        # Actualizare fază
                        if event == "start":
                            st.session_state.phase = "intro"
                        elif event == "confirm":
                            st.session_state.phase = "steps"
                        elif event in {"not_solved", "try_again"}:
                            st.session_state.phase = "alternatives"
                        elif event in {"solved", "done"}:
                            st.session_state.phase = "end"
                        # Actualizare butoane rapide NOUL set
                        new_qr = js.get("quick_replies", [])
                        # Dacă am trecut la steps, eliminăm Yes/No rămase accidental
                        if st.session_state.phase == "steps":
                            new_qr = [x for x in new_qr if x not in {"Yes", "No"}]
                        st.session_state.quick_replies = new_qr
                    break  # Evităm procesarea altor butoane în același rerender
            # Debug raw response mutat în sidebar pentru persistență

with tab3:  # TAB 3 - Feedback final
    st.header("Feedback")
    if not st.session_state.session_id:  # Nu există sesiune activă
        st.warning("Need an active session.")
    elif st.session_state.phase != "end":  # Nu am ajuns la finalul fluxului
        st.info("Finish troubleshooting to enable feedback.")
    else:
        solved = st.radio("Problem solved?", ["Yes", "No"], horizontal=True)  # Selectare rezultat
        notes_fb = st.text_area("Notes / suggestions")  # Observații utilizator
        if st.button("Submit Feedback"):
            import time
            start_ts = time.time()
            payload = {
                "session_id": st.session_state.session_id,
                "solved": solved == "Yes",
                "final_label": st.session_state.label,
                "notes": notes_fb,
            }
            url = f"{API_URL}/feedback"
            resp = requests.post(url, json=payload)
            elapsed = (time.time() - start_ts) * 1000
            if resp.status_code == 200:
                st.success("Thank you for your feedback!")
                st.session_state.api_logs.append({
                    "endpoint": "/feedback",
                    "method": "POST",
                    "status": resp.status_code,
                    "elapsed_ms": round(elapsed, 1),
                    "payload_summary": {"solved": solved == "Yes", "notes_len": len(notes_fb or "")},
                })
            else:
                st.error(f"Feedback error: {resp.text}")
                st.session_state.api_logs.append({
                    "endpoint": "/feedback",
                    "method": "POST",
                    "status": resp.status_code,
                    "elapsed_ms": round(elapsed, 1),
                    "error": resp.text[:200],
                })

with tab4:  # TAB 4 - Istoric conversație
    st.header("History")
    if not st.session_state.chat_history:  # Nimic de afișat încă
        st.write("No messages yet.")
    else:
        # Butoane utilitare pentru istoric: clear + export JSON/Markdown
        util_cols = st.columns(3)
        if util_cols[0].button("Clear History"):
            st.session_state.chat_history = []
            st.session_state.last_resp = None  # Ștergem și ultimul răspuns pentru consistență
            st.success("History cleared.")
        # Pregătim datele de export (generăm doar dacă există istoric actual)
        export_json = json.dumps([
            {"sender": s, "message": m} for s, m in st.session_state.chat_history
        ], ensure_ascii=False, indent=2)
        md_lines = ["# Chat History"]
        for s, m in st.session_state.chat_history:
            md_lines.append(f"**{s.capitalize()}:** {m}")
        export_md = "\n\n".join(md_lines)
        util_cols[1].download_button(
            "Export JSON",
            data=export_json,
            file_name="chat_history.json",
            mime="application/json",
        )
        util_cols[2].download_button(
            "Export Markdown",
            data=export_md,
            file_name="chat_history.md",
            mime="text/markdown",
        )
        for sender, msg in st.session_state.chat_history:
            st.markdown(f"- **{sender}:** {msg}")  # Listă simplă pentru copiere rapidă

st.caption("Fresh UI rebuilt from backend logic. Use sidebar for debug & reset.")  # Footer informativ
