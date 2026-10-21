"""Streamlit screens for the symptom check: step-by-step forms, results, and the sidebar with the moon."""
import html
import streamlit as st
from symptom_check import CONDITIONS, LOW_MATCH, STEPS, URGENT, progress, score, told, urgent

CSS = """
<style>
.sc-moon { display: flex; gap: 14px; align-items: center; margin: 4px 0 18px; }
.sc-moon b { font-size: 1.05rem; color: #4A0E1C; }
.sc-fine { font-size: .85rem; color: #9a5a69; line-height: 1.35; }
.sc-head { font-family: Georgia, serif; font-size: 1.2rem; color: #4A0E1C; margin: 18px 0 8px; }
.sc-chip { display: inline-block; background: #fff; border: 1px solid #f6c9d3; border-radius: 999px;
  padding: 4px 12px; margin: 0 6px 8px 0; font-size: .85rem; color: #4A0E1C; }
.sc-row { display: flex; justify-content: space-between; gap: 10px; font-size: .92rem; color: #4A0E1C; margin-top: 12px; }
.sc-row span:last-child { color: #9a5a69; font-variant-numeric: tabular-nums; }
.sc-row.top span:first-child { font-weight: 700; }
.sc-bar { height: 6px; background: #f9d9e1; border-radius: 999px; margin-top: 6px; overflow: hidden; }
.sc-bar i { display: block; height: 100%; background: linear-gradient(90deg, #E8537A, #C8102E); border-radius: 999px; }
.sc-step { font-size: .78rem; letter-spacing: .1em; font-weight: 700; color: #C8102E; text-transform: uppercase; }
.sc-urgent { background: #fff3e0; border-left: 4px solid #C8102E; padding: 10px 14px; border-radius: 8px; color: #4A0E1C; margin: 8px 0; }
.sc-result { background: #fff; border: 1px solid #f6c9d3; border-radius: 18px; padding: 16px 18px; margin: 10px 0;
  box-shadow: 0 2px 10px rgba(200,16,46,.06); color: #4A0E1C; }
.sc-result h3 { margin: 2px 0 6px; color: #8B0A1E; }
.sc-result a { color: #C8102E; }
[data-testid="stForm"] [data-testid="stWidgetLabel"] p { font-size: 1rem; font-weight: 600; color: #4A0E1C; }
</style>
"""


def _state():
    ss = st.session_state
    ss.setdefault("sc_step", 0)        # current form step; len(STEPS) = results
    ss.setdefault("sc_answers", {})    # {question_id: option_index}
    ss.setdefault("sc_round", 0)       # bumped on restart so the form widgets start empty
    return ss


def moon_svg(f, size=74):
    """A moon that fills in from the right as the questionnaire is answered (f = 0-1)."""
    r, c = size / 2 - 2, size / 2
    rx, sweep = abs(1 - 2 * f) * r, 0 if f < .5 else 1
    lit = "" if f <= .001 else (f'<circle cx="{c}" cy="{c}" r="{r}" fill="#FFF6F8"/>' if f >= .999 else
          f'<path d="M{c} {c - r} A{r} {r} 0 0 1 {c} {c + r} A{rx} {r} 0 0 {sweep} {c} {c - r}Z" fill="#FFF6F8"/>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">'
            f'<circle cx="{c}" cy="{c}" r="{r}" fill="#F4B3C4"/>{lit}'
            f'<circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="#EFA3B7" stroke-width="1.5"/></svg>')


def bars(matches, top_first=True):
    return "".join(
        f'<div class="sc-row{" top" if top_first and i == 0 else ""}"><span>{html.escape(m["name"])}</span>'
        f'<span>{m["percent"]}%</span></div><div class="sc-bar"><i style="width:{m["percent"]}%"></i></div>'
        for i, m in enumerate(matches))


def _save(step, move):
    """Form callback: store this step's answers, then go back or forward."""
    ss = _state()
    for q in STEPS[step]["questions"]:
        labels = [o[0] for o in q["options"]]
        v = ss.get(f"sc{ss.sc_round}_{q['id']}")
        if v in labels:
            ss.sc_answers[q["id"]] = labels.index(v)
        else:
            ss.sc_answers.pop(q["id"], None)
    ss.sc_step = max(0, min(step + move, len(STEPS)))


def restart():
    ss = _state()
    ss.sc_answers, ss.sc_step, ss.sc_round = {}, 0, ss.sc_round + 1


def _goto(step):
    _state().sc_step = step


def render_tab():
    ss = _state()
    st.markdown(CSS, unsafe_allow_html=True)
    if ss.sc_step < len(STEPS):
        step = STEPS[ss.sc_step]
        with st.chat_message("assistant", avatar="🌙"):
            if ss.sc_step == 0 and not ss.sc_answers:
                st.markdown("I'll ask a few short questions about your periods and body, then show which of "
                            "**PCOS**, **endometriosis** or **uterine fibroids** your answers fit most closely. "
                            "Skip anything you'd rather not answer.")
            st.markdown(f'<div class="sc-step">Step {ss.sc_step + 1} of {len(STEPS)} · {step["title"]}</div>'
                        f'{html.escape(step["intro"])}', unsafe_allow_html=True)
        with st.form(f"sc_form_{ss.sc_round}_{ss.sc_step}"):
            for q in step["questions"]:
                labels = [o[0] for o in q["options"]]
                st.radio(q["text"], labels, index=ss.sc_answers.get(q["id"]), key=f"sc{ss.sc_round}_{q['id']}")
            last = ss.sc_step == len(STEPS) - 1
            if ss.sc_step > 0:
                back, nxt = st.columns([1, 2])
                back.form_submit_button("← Back", on_click=_save, args=(ss.sc_step, -1), use_container_width=True)
            else:
                nxt = st.container()
            nxt.form_submit_button("See my results" if last else "Next →", type="primary",
                                   on_click=_save, args=(ss.sc_step, 1), use_container_width=True)
        if urgent(ss.sc_answers):
            st.markdown(f'<div class="sc-urgent">{html.escape(URGENT)}</div>', unsafe_allow_html=True)
    else:
        _results(ss)
    st.caption("🩺 This compares your answers with common patterns described by the NHS and MedlinePlus. "
               "It is not a diagnosis. Only a clinician can diagnose these conditions.")


def _results(ss):
    matches = score(ss.sc_answers)
    if urgent(ss.sc_answers):
        st.markdown(f'<div class="sc-urgent">{html.escape(URGENT)}</div>', unsafe_allow_html=True)
    top = matches[0]
    if top["percent"] < LOW_MATCH:
        st.markdown('<div class="sc-result"><h3>No strong match</h3>Your answers don\'t closely fit PCOS, '
                    'endometriosis or uterine fibroids. Period symptoms have many other causes, so if something '
                    'is bothering you or affecting your life, it\'s still worth talking to a GP.</div>',
                    unsafe_allow_html=True)
    else:
        c = CONDITIONS[top["id"]]
        chips = "".join(f'<span class="sc-chip">{html.escape(s)}</span>' for s in top["signs"])
        links = "<br>".join(f'{n}. <a href="{u}" target="_blank" rel="noopener">{html.escape(t)}</a>'
                            for n, (t, u) in enumerate(c["sources"], 1))
        st.markdown(f'<div class="sc-result"><div class="sc-step">Closest pattern</div>'
                    f'<h3>{html.escape(c["name"])} · {top["percent"]}% match</h3>'
                    f'<p>{html.escape(c["summary"])}</p><b>What fits from your answers</b><br>{chips}'
                    f'<p><b>What to do next:</b> {html.escape(c["next"])}</p>'
                    f'<div class="sc-fine">📚 Sources<br>{links}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sc-head">How the three patterns compare</div>' + bars(matches), unsafe_allow_html=True)
    st.markdown('<p class="sc-fine" style="margin-top:12px">These conditions share several signs, and it\'s possible '
                'to have more than one. A higher match means more of that condition\'s typical signs appear in '
                'your answers, not that you have it.</p>', unsafe_allow_html=True)
    a, b = st.columns(2)
    a.button("Change my answers", on_click=_goto, args=(0,), use_container_width=True)
    b.button("Start a new symptom check", on_click=restart, use_container_width=True, key="sc_restart_main")


def render_sidebar():
    ss = _state()
    f = progress(ss.sc_answers)
    with st.sidebar:
        st.markdown(CSS + f'<div class="sc-moon">{moon_svg(f)}<div><b>{round(f * 100)}% of the picture</b>'
                    f'<div class="sc-fine">Each answer helps Luna understand you better.</div></div></div>',
                    unsafe_allow_html=True)
        signs = told(ss.sc_answers)
        st.markdown('<div class="sc-head">What you\'ve told Luna</div>' + (
            "".join(f'<span class="sc-chip">{html.escape(s)}</span>' for s in signs)
            or '<span class="sc-fine">Nothing yet. Open the Symptom check tab to start.</span>'), unsafe_allow_html=True)
        matches = [m for m in score(ss.sc_answers) if m["percent"] > 0]
        st.markdown('<div class="sc-head">Closest patterns so far</div>' + (
            bars(matches) or '<span class="sc-fine">Patterns appear as you answer.</span>'), unsafe_allow_html=True)
        st.write("")
        st.button("Start a new symptom check", on_click=restart, use_container_width=True, key="sc_restart_side")
        st.markdown('<p class="sc-fine" style="margin-top:14px">Luna is for information only and is not a diagnosis.</p>',
                    unsafe_allow_html=True)
