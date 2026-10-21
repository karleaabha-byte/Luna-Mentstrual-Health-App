"""Form-based symptom check: which of PCOS, endometriosis or uterine fibroids the answers fit most closely.

Each answer option carries points for the conditions it is a typical sign of (from the NHS and MedlinePlus
pages in knowledge/). A condition's match is the share of its possible points the user's answers reach, so it
grows as more of its typical signs are reported. Deterministic and explainable; educational, not a diagnosis.
"""

CONDITIONS = {
    "pcos": {
        "name": "Polycystic ovary syndrome (PCOS)",
        "summary": "A common hormonal condition that affects how the ovaries work. Its main features are irregular "
                   "or missed periods and signs of higher androgen levels, such as extra facial or body hair, "
                   "oily skin or acne. Weight gain and thinning hair on the head are also common.",
        "next": "A GP can check your hormone levels with a blood test and may arrange an ultrasound scan of your ovaries.",
        "sources": [("NHS: Polycystic ovary syndrome (PCOS)", "https://www.nhs.uk/conditions/polycystic-ovary-syndrome-pcos/"),
                    ("MedlinePlus: Polycystic Ovary Syndrome", "https://medlineplus.gov/polycysticovarysyndrome.html")],
    },
    "endometriosis": {
        "name": "Endometriosis",
        "summary": "Tissue similar to the womb lining grows elsewhere, such as the ovaries, pelvis, bladder or bowel. "
                   "It typically causes severe period pain, pain in the lower tummy and back, pain when pooing or "
                   "peeing, and pain during or after sex.",
        "next": "Tell a GP about your symptoms, how long you've had them and how they affect your life. "
                "Keeping a pain diary can help. They may refer you to a gynaecologist.",
        "sources": [("NHS: Endometriosis", "https://www.nhs.uk/conditions/endometriosis/"),
                    ("MedlinePlus: Endometriosis", "https://medlineplus.gov/endometriosis.html")],
    },
    "fibroids": {
        "name": "Uterine fibroids",
        "summary": "Non-cancerous growths in or around the womb. Many people have no symptoms, but they can cause "
                   "heavy or painful periods, tummy or lower-back pain, needing to pee more often, constipation "
                   "or bloating, and discomfort during sex.",
        "next": "A GP can examine your tummy and may arrange an ultrasound scan to look for fibroids.",
        "sources": [("NHS: Fibroids", "https://www.nhs.uk/conditions/fibroids/"),
                    ("MedlinePlus: Uterine Fibroids", "https://medlineplus.gov/uterinefibroids.html")],
    },
}

# Each option: (label, {condition: points}, what it adds to "What you've told Luna" or None).
NOT_SURE = ("Not sure", {}, None)
STEPS = [
    {"title": "Your cycle", "intro": "Let's start with your periods themselves.", "questions": [
        {"id": "regularity", "text": "How regular are your periods?", "options": [
            ("Regular (every 21 to 35 days)", {}, None),
            ("Often irregular or hard to predict", {"pcos": 3}, "Irregular periods"),
            ("Very infrequent (fewer than 8 a year) or they've stopped", {"pcos": 4}, "Infrequent or missed periods"),
            NOT_SURE]},
        {"id": "heaviness", "text": "How heavy are your periods?", "options": [
            ("Light or normal", {}, None),
            ("Heavy: I change a pad or tampon every 1 to 2 hours, double up, or bleed through", {"fibroids": 3, "endometriosis": 1}, "Heavy periods"),
            NOT_SURE]},
        {"id": "length", "text": "How long does your bleeding usually last?", "options": [
            ("7 days or less", {}, None),
            ("More than 7 days", {"fibroids": 2}, "Periods longer than 7 days"),
            NOT_SURE]},
        {"id": "faint", "text": "Do you feel faint, dizzy or very short of breath during heavy bleeding?", "options": [
            ("No", {}, None),
            ("Yes", {"fibroids": 1}, "Faint or dizzy when bleeding"),
            NOT_SURE]},
    ]},
    {"title": "Pain", "intro": "Now a few questions about pain. Answer for a typical month.", "questions": [
        {"id": "period_pain", "text": "How bad is your period pain?", "options": [
            ("None or mild", {}, None),
            ("Moderate: painkillers usually help", {"endometriosis": 1, "fibroids": 1}, "Period pain"),
            ("Severe: it stops me doing normal things, even with painkillers", {"endometriosis": 4, "fibroids": 1}, "Severe period pain"),
            NOT_SURE]},
        {"id": "pelvic_pain", "text": "Do you get pain in your lower tummy or lower back outside your period?", "options": [
            ("No", {}, None),
            ("Yes", {"endometriosis": 2, "fibroids": 2}, "Tummy or back pain outside periods"),
            NOT_SURE]},
        {"id": "toilet_pain", "text": "Does it hurt when you poo or pee, especially around your period?", "options": [
            ("No", {}, None),
            ("Yes", {"endometriosis": 3, "fibroids": 1}, "Pain when pooing or peeing"),
            NOT_SURE]},
        {"id": "sex_pain", "text": "Do you have pain during or after sex?", "options": [
            ("No", {}, None),
            ("Yes", {"endometriosis": 3, "fibroids": 1}, "Pain during or after sex"),
            ("Doesn't apply to me", {}, None),
            NOT_SURE]},
    ]},
    {"title": "Skin, hair and weight", "intro": "These can be linked to hormone levels.", "questions": [
        {"id": "hair", "text": "Do you have extra hair on your face, chest, back or tummy?", "options": [
            ("No", {}, None),
            ("Yes", {"pcos": 4}, "Extra facial or body hair"),
            NOT_SURE]},
        {"id": "skin", "text": "Do you have oily skin or acne that's hard to get rid of?", "options": [
            ("No", {}, None),
            ("Yes", {"pcos": 2}, "Oily skin or acne"),
            NOT_SURE]},
        {"id": "weight", "text": "Have you gained weight, or found it hard to lose weight, without a clear reason?", "options": [
            ("No", {}, None),
            ("Yes", {"pcos": 2}, "Weight gain"),
            NOT_SURE]},
        {"id": "thinning", "text": "Is the hair on your head thinning or falling out?", "options": [
            ("No", {}, None),
            ("Yes", {"pcos": 2}, "Thinning hair on the head"),
            NOT_SURE]},
    ]},
    {"title": "Other changes", "intro": "Last few. These help tell the three patterns apart.", "questions": [
        {"id": "bladder", "text": "Do you need to pee more often or more suddenly than usual?", "options": [
            ("No", {}, None),
            ("Yes", {"fibroids": 2}, "Peeing more often"),
            NOT_SURE]},
        {"id": "bowel", "text": "Do you often feel bloated or constipated?", "options": [
            ("No", {}, None),
            ("Yes", {"fibroids": 2, "endometriosis": 1}, "Bloating or constipation"),
            NOT_SURE]},
        {"id": "tired", "text": "Do you feel extremely tired a lot of the time?", "options": [
            ("No", {}, None),
            ("Yes", {"endometriosis": 1, "fibroids": 1}, "Extreme tiredness"),
            NOT_SURE]},
        {"id": "pregnancy", "text": "If you've tried to get pregnant, has it been difficult?", "options": [
            ("I haven't tried / doesn't apply", {}, None),
            ("No, it wasn't difficult", {}, None),
            ("Yes, it's been difficult", {"pcos": 2, "endometriosis": 2, "fibroids": 1}, "Difficulty getting pregnant"),
            NOT_SURE]},
    ]},
]
QUESTIONS = {q["id"]: q for s in STEPS for q in s["questions"]}
URGENT = ("If you're bleeding very heavily and feel faint or dizzy, or you have sudden severe pain, get medical "
          "help urgently: call NHS 111 or your local emergency number.")
LOW_MATCH = 25  # below this, the answers don't really fit any of the three patterns


def _max_points():
    best = {c: 0 for c in CONDITIONS}
    for q in QUESTIONS.values():
        for c in CONDITIONS:
            best[c] += max(opt[1].get(c, 0) for opt in q["options"])
    return best


MAX_POINTS = _max_points()


def clean(answers):
    """Keep only known question ids with a valid option index ({question_id: option_index})."""
    return {q: i for q, i in (answers or {}).items()
            if q in QUESTIONS and isinstance(i, int) and 0 <= i < len(QUESTIONS[q]["options"])}


def progress(answers):
    """Share of the questionnaire answered, 0-1 (drives the moon)."""
    return len(clean(answers)) / len(QUESTIONS)


def told(answers):
    """Short labels for the signs the user has reported, in question order."""
    a = clean(answers)
    return [QUESTIONS[q]["options"][a[q]][2] for q in QUESTIONS if q in a and QUESTIONS[q]["options"][a[q]][2]]


def score(answers):
    """Conditions ranked by match (0-100), each with the reported signs that fit it."""
    a = clean(answers)
    out = []
    for cid, c in CONDITIONS.items():
        pts, signs = 0, []
        for q, i in a.items():
            label, weights, sign = QUESTIONS[q]["options"][i]
            if weights.get(cid):
                pts += weights[cid]
                signs.append(sign)
        out.append({"id": cid, "name": c["name"], "percent": round(100 * pts / MAX_POINTS[cid]), "signs": signs})
    return sorted(out, key=lambda m: m["percent"], reverse=True)


def urgent(answers):
    """Feeling faint or dizzy with heavy bleeding needs prompt medical advice, whatever the match."""
    return clean(answers).get("faint") == 1
