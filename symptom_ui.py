"""Streamlit screens for the symptom check: step-by-step forms, results, and the sidebar with the moon."""
import html
import streamlit as st
from symptom_check import CONDITIONS, LOW_MATCH, STEPS, URGENT, progress, score, told, urgent

LUNA_AVATAR = "static/luna-avatar.svg"  # pink circle with a white crescent, as in the chat

CSS = """
<style>
.sc-moon { display: flex; gap: 16px; align-items: center; margin: 8px 0 26px; }
.sc-moon b { font-size: 1.15rem; font-weight: 600; color: #3D0F1F; }
.sc-fine { font-size: .9rem; color: #8A5566; line-height: 1.45; }
.sc-head { font-family: "Newsreader", Georgia, serif; font-size: 1.45rem; font-weight: 500; color: #3D0F1F; margin: 22px 0 12px; }
.sc-chip { display: inline-block; background: #fff; border: 1px solid #EBD3DA; border-radius: 999px;
  padding: 6px 14px; margin: 0 6px 10px 0; font-size: .92rem; color: #3D0F1F; }
.sc-row { display: flex; justify-content: space-between; gap: 10px; font-size: 1rem; color: #3D0F1F; margin-top: 16px; }
.sc-row span:last-child { color: #8A5566; font-variant-numeric: tabular-nums; }
.sc-row.top span:first-child { font-weight: 700; }
.sc-bar { height: 7px; background: #F6D9E1; border-radius: 999px; margin-top: 8px; overflow: hidden; }
.sc-bar i { display: block; height: 100%; background: linear-gradient(90deg, #E2638E, #D9507E); border-radius: 999px; }
.sc-step { font-size: .78rem; letter-spacing: .1em; font-weight: 700; color: #D63A5E; text-transform: uppercase; margin-top: 4px; }
.sc-urgent { background: #FFF3F0; border-left: 4px solid #D63A5E; padding: 10px 14px; border-radius: 8px; color: #3D0F1F; margin: 8px 0; }
.sc-result { background: #fff; border: 1px solid #EBD3DA; border-radius: 18px; padding: 18px 20px; margin: 10px 0;
  box-shadow: 0 2px 12px rgba(214,58,94,.06); color: #3D0F1F; }
.sc-result h3 { font-family: "Newsreader", Georgia, serif; font-weight: 500; margin: 2px 0 8px; color: #3D0F1F; }
.sc-result a { color: #D63A5E; }
[data-testid="stForm"] { background: #fff; border: 1px solid #EBD3DA; border-radius: 18px; padding: 18px 22px; }
[data-testid="stForm"] [data-testid="stWidgetLabel"] p { font-size: 1.05rem; font-weight: 600; color: #3D0F1F; }
</style>
"""


def _state():
    ss = st.session_state
    ss.setdefault("sc_step", 0)        # current form step; len(STEPS) = results
    ss.setdefault("sc_answers", {})    # {question_id: option_index}
    ss.setdefault("sc_round", 0)       # bumped on restart so the form widgets start empty
    return ss


# Lunar "seas" (maria) and craters, roughly where they sit on the real near side: (cx, cy, rx, ry, angle).
_MARIA = [(37, 33, 11, 8, -20), (57, 31, 6.5, 6, 0), (63, 45, 8, 6, 15), (27, 52, 9, 14, 10), (42, 66, 7.5, 5, 0),
          (77, 37, 4.5, 3.6, 0), (72, 57, 5, 7.5, -10), (52, 50, 4, 3, 0), (35, 76, 4, 2.6, 0)]
_CRATERS = [(46, 83, 2.4), (31, 41, 1.7), (55, 71, 1.5), (68, 22, 1.3), (22, 63, 1.4), (80, 66, 1.2), (60, 86, 1.1)]


def moon_svg(f, size=84):
    """A realistic moon whose lit part grows from the right as the questionnaire is answered (f = 0-1)."""
    R, C = 45, 50
    rx, sweep = abs(1 - 2 * f) * R, 0 if f < .5 else 1
    lit = ("" if f <= .001 else f'<circle cx="{C}" cy="{C}" r="{R}" fill="#fff"/>' if f >= .999 else
           f'<path d="M{C} {C - R} A{R} {R} 0 0 1 {C} {C + R} A{rx:.2f} {R} 0 0 {sweep} {C} {C - R}Z" fill="#fff"/>')
    maria = lambda fill, op: "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="{a}" ry="{b}" transform="rotate({t} {x} {y})" fill="{fill}" opacity="{op}"/>'
        for x, y, a, b, t in _MARIA)
    craters = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#d9bcc6" stroke="#fffaf8" stroke-width=".6" '
                      f'stroke-opacity=".8"/>' for x, y, r in _CRATERS)
    u = f"{round(f * 1000)}-{size}"  # unique ids, so several moons can share a page
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 100 100" aria-hidden="true">
<defs>
  <radialGradient id="mLit{u}" cx=".62" cy=".36" r=".78"><stop offset="0" stop-color="#fffdf9"/>
    <stop offset=".6" stop-color="#f7ebee"/><stop offset="1" stop-color="#e2c4cf"/></radialGradient>
  <radialGradient id="mDark{u}" cx=".4" cy=".38" r=".8"><stop offset="0" stop-color="#e8b9c7"/>
    <stop offset="1" stop-color="#c78fa3"/></radialGradient>
  <radialGradient id="mLimb{u}" cx=".5" cy=".5" r=".5"><stop offset=".78" stop-color="#7a3a52" stop-opacity="0"/>
    <stop offset="1" stop-color="#7a3a52" stop-opacity=".28"/></radialGradient>
  <filter id="mSoft{u}" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1.6"/></filter>
  <filter id="mGlow{u}" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3.2"/></filter>
  <mask id="mPhase{u}"><rect width="100" height="100" fill="#000"/><g filter="url(#mSoft{u})">{lit}</g></mask>
  <clipPath id="mDisc{u}"><circle cx="{C}" cy="{C}" r="{R}"/></clipPath>
</defs>
<circle cx="{C}" cy="{C}" r="{R + 2}" fill="#ffc4d4" opacity="{.25 + .55 * f:.2f}" filter="url(#mGlow{u})"/>
<g clip-path="url(#mDisc{u})">
  <circle cx="{C}" cy="{C}" r="{R}" fill="url(#mDark{u})"/>{maria("#a86f84", .35)}
  <g mask="url(#mPhase{u})"><circle cx="{C}" cy="{C}" r="{R}" fill="url(#mLit{u})"/>{maria("#c9a6b2", .75)}{craters}</g>
  <circle cx="{C}" cy="{C}" r="{R}" fill="url(#mLimb{u})"/>
</g>
<circle cx="{C}" cy="{C}" r="{R}" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width=".8"/>
</svg>"""


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
        with st.chat_message("assistant", avatar=LUNA_AVATAR):
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


def render_sidebar(footer=""):
    ss = _state()
    f = progress(ss.sc_answers)
    with st.sidebar:
        st.markdown(CSS + f'<div class="sc-moon">{moon_svg(f)}<div><b>{round(f * 100)}% of the picture</b>'
                    f'<div class="sc-fine">Each answer helps Luna understand you better.</div></div></div>',
                    unsafe_allow_html=True)
        signs = told(ss.sc_answers)
        st.markdown('<div class="sc-head">What you\'ve told Luna</div>' + (
            "".join(f'<span class="sc-chip">{html.escape(s)}</span>' for s in signs)
            or '<span class="sc-fine">Nothing yet. Answer the symptom check to fill this in.</span>'), unsafe_allow_html=True)
        matches = [m for m in score(ss.sc_answers) if m["percent"] > 0]
        st.markdown('<div class="sc-head">Closest patterns so far</div>' + (
            bars(matches) or '<span class="sc-fine">Patterns appear as you answer.</span>'), unsafe_allow_html=True)
        st.write("")
        st.button("Start a new symptom check", on_click=restart, use_container_width=True, key="sc_restart_side")
        st.markdown(f'<p class="sc-fine" style="margin-top:26px">Luna is for information only and is not a diagnosis. '
                    f'{html.escape(footer)}</p>', unsafe_allow_html=True)
