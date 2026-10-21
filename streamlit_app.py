"""Streamlit version of Luna (for Streamlit Community Cloud). Run: streamlit run streamlit_app.py"""
import os, sys
from datetime import date, timedelta

# Streamlit Cloud's system sqlite can be too old for Chroma; use the bundled one if available.
try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)  # always use the latest .env values (Streamlit reruns keep old env vars)
# On Streamlit Cloud, keys come from App settings -> Secrets (same names as .env).
try:
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))
except Exception:
    pass

from rag import KnowledgeBase, answer_question, general_answer
import symptom_ui

st.set_page_config(page_title="Luna · period care", page_icon="🩸", layout="centered")

# ---------- styling (soft pink, serif headings) ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp textarea {
  font-family: "Hanken Grotesk", "Segoe UI", system-ui, sans-serif; }
.stApp { background: linear-gradient(180deg, #FFE9EF 0%, #FFF4F7 38%, #FFFAFB 100%); color: #3D0F1F; }
.block-container { padding-top: 2.6rem; max-width: 900px; }
section[data-testid="stSidebar"] { background: #FCE4EC; border-right: 1px solid #F4C9D6; }
section[data-testid="stSidebar"][aria-expanded="true"] { width: 360px !important; min-width: 360px !important; }
.luna-title { display: flex; align-items: center; gap: 14px; margin: 0; }
.luna-title h1 { font-family: "Newsreader", Georgia, serif !important; font-weight: 500; font-size: 3.6rem;
  line-height: 1; color: #3D0F1F; margin: 0; padding: 0; letter-spacing: -.01em; }
.luna-sub { color: #8A5566; font-size: 1.18rem; margin: 10px 0 22px; }
[data-testid="stButtonGroup"] button { background: #fff; border: 1px solid #E5D3D9; color: #3D0F1F;
  font-size: 1.02rem; padding: 6px 18px; }
[data-testid="stButtonGroup"] button[kind$="Active"] { background: #FDE2E8; border-color: #EC8FA8; color: #D63A5E; }
[data-testid="stButtonGroup"] button p { font-size: 1.02rem; }
[data-testid="stChatMessage"] { background: transparent; padding: 6px 0; gap: 14px; }
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li { font-size: 1.15rem; line-height: 1.65; color: #3D0F1F; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #FDE2E8;
  border: 1px solid #F6C9D3; border-radius: 18px; padding: 10px 20px; width: fit-content; max-width: 85%; }
[data-testid="stChatMessageAvatarUser"] { display: none; }
[data-testid="stChatMessage"] img { border-radius: 50%; width: 2.6rem; height: 2.6rem; }
[data-testid="stChatMessage"] a { color: #D63A5E; }
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: #FFFAFB; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { background: #F2EFF4; border-color: #ECE6EE; border-radius: 14px; }
[data-testid="stChatInput"] textarea { font-size: 1.08rem; color: #3D0F1F; }
.stButton > button, .stFormSubmitButton > button { border-radius: 12px; font-weight: 600; }
.stButton > button[kind="secondary"] { background: #fff; border: 1px solid #E5D3D9; color: #3D0F1F; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
  background: linear-gradient(90deg, #E2638E, #D9507E); border: 0; color: #fff; }
.card { background: #fff; border: 1px solid #EBD3DA; border-radius: 18px; padding: 16px 18px; margin: 10px 0;
  box-shadow: 0 2px 12px rgba(214,58,94,.06); color: #3D0F1F; }
.next { background: linear-gradient(135deg, #E2638E, #D9507E); color: #fff; text-align: center; }
.next small { letter-spacing: .12em; opacity: .85; font-weight: 700; }
.next .big { font-family: "Newsreader", Georgia, serif; font-size: 2.1rem; font-weight: 500; margin: 4px 0; }
.phase-bar { display: flex; height: 14px; border-radius: 999px; overflow: hidden; margin: 10px 0 4px; }
.phase-bar div { height: 100%; }
.legend span { font-size: .78rem; margin-right: 12px; color: #8A5566; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.log { display: flex; justify-content: space-between; border-bottom: 1px dashed #EBD3DA; padding: 8px 0; }
.log:last-child { border-bottom: 0; }
.muted { color: #8A5566; font-size: .82rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading Luna's health library…")
def get_kb():
    kb = KnowledgeBase()
    kb.ingest("knowledge/sources.json")
    return kb


kb = get_kb()
llm_on = bool(os.getenv("LLM_API_KEY"))
CRESCENT = ("""<svg width="54" height="54" viewBox="0 0 64 64" aria-hidden="true"><defs>
<linearGradient id="lc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3A3BC"/><stop offset="1" stop-color="#D9507E"/></linearGradient>
<mask id="lm"><rect width="64" height="64" fill="#000"/><circle cx="30" cy="33" r="24" fill="#fff"/><circle cx="43" cy="24" r="21" fill="#000"/></mask>
</defs><rect width="64" height="64" fill="url(#lc)" mask="url(#lm)"/></svg>""")
st.markdown(f'<div class="luna-title">{CRESCENT}<h1>Luna</h1></div>'
            '<p class="luna-sub">A gentle guide to your period, grounded in NHS, MedlinePlus and ACOG advice.</p>',
            unsafe_allow_html=True)

MODES = ["Symptom check", "Ask about periods", "Cycle tracker"]
if hasattr(st, "segmented_control"):
    mode = st.segmented_control("Mode", MODES, default=MODES[0], key="mode", label_visibility="collapsed") or MODES[0]
else:  # older Streamlit
    mode = st.radio("Mode", MODES, horizontal=True, key="mode", label_visibility="collapsed")

# ---------- symptom check (forms + moon in the sidebar) ----------
if mode == MODES[0]:
    symptom_ui.render_tab()
symptom_ui.render_sidebar(
    f"AI writing is {'on' if llm_on else 'off: add LLM_API_KEY in Secrets for full replies'}. "
    f"Search: {'semantic' if kb.mode.startswith('semantic') else 'keyword'}.")

# ---------- chat ----------
if mode == MODES[1]:
    if "msgs" not in st.session_state:
        st.session_state.msgs = [{"role": "assistant", "content":
            "Hi, I'm Luna. Ask me anything about periods, cramps, PCOS, products or your cycle. "
            "I answer from trusted health sources and show you where it came from."}]
    for m in st.session_state.msgs:
        with st.chat_message(m["role"], avatar=symptom_ui.LUNA_AVATAR if m["role"] == "assistant" else None):
            st.markdown(m["content"])
    offer = st.session_state.get("offer")
    if offer:
        a, b = st.columns([2, 1])
        if a.button("✨ Yes, answer with AI", type="primary", use_container_width=True):
            st.session_state.offer = None
            try:
                with st.spinner("Asking the AI…"):
                    st.session_state.msgs.append({"role": "assistant", "content": general_answer(offer, st.session_state.msgs[:-2])})
            except Exception as e:
                st.session_state.msgs.append({"role": "assistant", "content": f"Sorry, the AI provider returned an error: {e}"})
            st.rerun()
        if b.button("No thanks", use_container_width=True):
            st.session_state.offer = None
            st.rerun()
    if len(st.session_state.msgs) == 1:
        cols = st.columns(3)
        for col, q in zip(cols, ["What is PCOS?", "Are bad cramps normal?", "Is my period too heavy?"]):
            if col.button(q, use_container_width=True):
                st.session_state.pending = q
                st.rerun()
    st.caption("🩺 Educational information only — not a diagnosis. For severe pain, very heavy bleeding or "
               "feeling faint, contact a doctor or emergency services.")

    q = st.chat_input("Ask anything about periods, symptoms or products") or st.session_state.pop("pending", None)
else:
    q = None
if q:
    st.session_state.msgs.append({"role": "user", "content": q})
    st.session_state.offer = None
    try:
        with st.spinner("Checking trusted sources…"):
            r = answer_question(q, kb, history=st.session_state.msgs[:-1])  # earlier messages give context
        text = r["answer"]
        if r.get("offer_general"):
            st.session_state.offer = q
        if r["sources"]:
            text += "\n\n---\n**📚 Sources**\n" + "\n".join(f"{s['n']}. [{s['title']}]({s['url']})" for s in r["sources"])
    except Exception as e:
        text = ("The AI provider is rate-limiting requests (free plan limit). Wait a minute and ask again."
                if "429" in str(e) else f"Sorry, the AI provider returned an error: {e}")
    st.session_state.msgs.append({"role": "assistant", "content": text})
    st.rerun()

# ---------- tracker ----------
PHASES = [("Period", "#C8102E"), ("Follicular", "#F48FB1"), ("Ovulation (est.)", "#8E24AA"), ("Luteal", "#F8BBD0")]

if mode == MODES[2]:
    logs = st.session_state.setdefault("logs", [])
    c1, c2, c3 = st.columns(3)
    start = c1.date_input("Period started", value=None)
    end = c2.date_input("Period ended", value=None)
    cycle = int(c3.number_input("Cycle length (days)", 15, 60, 28))
    if st.button("🩸 Save period", type="primary"):
        if not start or not end or end < start:
            st.error("Enter a start and an end date (end on or after start).")
        else:
            logs.append((start, end))
            logs.sort(reverse=True)
            st.success("Saved for this session.")

    if logs:
        last_start, last_end = logs[0]
        period_len = (last_end - last_start).days + 1
        nxt = last_start + timedelta(days=cycle)
        day = (date.today() - last_start).days % cycle + 1
        ovu = max(cycle - 14, period_len + 1)  # ovulation ~14 days before next period
        if day <= period_len: phase = PHASES[0]
        elif day < ovu - 1: phase = PHASES[1]
        elif day <= ovu + 1: phase = PHASES[2]
        else: phase = PHASES[3]
        widths = [period_len, max(ovu - 2 - period_len, 0), 3, max(cycle - ovu - 1, 0)]
        bar = "".join(f'<div style="width:{w / cycle * 100:.1f}%;background:{c}"></div>' for w, (_, c) in zip(widths, PHASES))
        marker = f'<div class="muted" style="margin-left:{(day - 0.5) / cycle * 100:.1f}%">▲ today</div>'
        legend = "".join(f'<span><i class="dot" style="background:{c}"></i>{n}</span>' for n, c in PHASES)

        st.markdown(f"""
<div class="card next"><small>NEXT PERIOD (ESTIMATE)</small>
  <div class="big">{nxt:%d %b %Y}</div>
  <div>{max((nxt - date.today()).days, 0)} days to go · you're on day {day} of {cycle}</div></div>
<div class="card"><b>Where you are in your cycle</b>
  <span class="muted"> — now: <b style="color:{phase[1]}">{phase[0]}</b></span>
  <div class="phase-bar">{bar}</div>{marker}<div class="legend">{legend}</div></div>
""", unsafe_allow_html=True)

        rows = "".join(f'<div class="log"><span>🩸 {s:%d %b %Y}</span>'
                       f'<span class="muted">{(e - s).days + 1} days · ended {e:%d %b}</span></div>' for s, e in logs)
        st.markdown(f'<div class="card"><b>Past periods</b>{rows}</div>', unsafe_allow_html=True)
        if st.button("Delete all logs"):
            logs.clear()
            st.rerun()
    else:
        st.markdown('<div class="card muted">Log your last period to see your next estimated date and cycle phase.</div>',
                    unsafe_allow_html=True)
    st.caption("Estimates assume a regular cycle and are not contraception or fertility advice. "
               "Logs are kept for this browser session only.")
