"""Local semantic RAG pipeline: chunking + MiniLM (ONNX, no PyTorch) + Chroma (cosine), keyword fallback.

answer_question() returns `contexts` (the exact text passed to the LLM) so the output can be
scored directly with RAGAS (user_input / retrieved_contexts / response / reference).
"""
import json, logging, os, re
from pathlib import Path

log = logging.getLogger(__name__)

SYSTEM_PROMPT = "You provide evidence-grounded health education."
PROMPT_TEMPLATE = (
    "You are Luna, a warm, concise menstrual-health education assistant. Not a diagnostic service. "
    "Answer the exact question in age-appropriate, nonjudgmental language. Use ONLY evidence in the supplied excerpts; "
    "do not invent facts or citations. If evidence is insufficient, say so. Give proportionate urgent-care guidance "
    "when clearly warranted. Cite claims inline as [1], [2], matching the excerpt numbers. Keep the answer under 220 words; use short paragraphs or bullet points when listing symptoms or steps."
    "\n\nExcerpts:\n{context}\n\nQuestion: {question}"
)
NO_EVIDENCE = ("I couldn't find enough reliable information in my small source library to answer that confidently. "
               "Try rephrasing, or ask a clinician or pharmacist for advice tailored to you.")


def get_embedder():
    """all-MiniLM-L6-v2 via ONNX Runtime (bundled with chromadb) - no PyTorch needed.
    Returns a callable: list[str] -> list[list[float]] (unit-normalised)."""
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    ef = DefaultEmbeddingFunction()
    return lambda texts: [[float(x) for x in v] for v in ef(list(texts))]


def chunk_text(text, max_words=120, overlap_sentences=1):
    """Sentence-aware chunking with a one-sentence overlap. Short docs stay a single chunk."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    chunks, cur = [], []
    for s in sents:
        if cur and len(" ".join(cur + [s]).split()) > max_words:
            chunks.append(" ".join(cur))
            cur = cur[-overlap_sentences:] if overlap_sentences else []
        cur.append(s)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


class KnowledgeBase:
    def __init__(self, min_score=None):
        self.docs, self.chunks = [], []
        self.collection = self.embedder = None
        self.mode = "keyword fallback"
        # Cosine similarity floor: below this a hit is treated as irrelevant (enables "I don't know").
        self.min_score = float(min_score if min_score is not None else os.getenv("MIN_RELEVANCE", "0.30"))

    def ingest(self, registry_path):
        """Load curated sources.json plus web_sources.json (from ingest.py) if present, chunk and index them."""
        registry_path = Path(registry_path)
        self.docs = json.loads(registry_path.read_text(encoding="utf-8"))
        web = registry_path.with_name("web_sources.json")
        if web.exists():
            self.docs += json.loads(web.read_text(encoding="utf-8"))
        self.chunks = [
            {**{k: d[k] for k in ("title", "url")}, "doc_id": d["id"], "id": f"{d['id']}#{i}", "text": c,
             "keywords": d.get("keywords", [])}
            for d in self.docs for i, c in enumerate(chunk_text(d["text"]))
        ]
        try:
            import chromadb, hashlib
            self.embedder = get_embedder()
            client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", ".chroma"))
            fingerprint = hashlib.sha1(json.dumps([(c["id"], c["text"]) for c in self.chunks]).encode()).hexdigest()
            try:
                col = client.get_collection("luna_health_sources")
                reuse = (col.metadata or {}).get("fingerprint") == fingerprint and col.count() == len(self.chunks)
            except Exception:
                col, reuse = None, False
            if reuse:  # sources unchanged since last run: skip re-embedding (fast startup)
                self.collection = col
            else:
                if col is not None:
                    client.delete_collection("luna_health_sources")
                self.collection = client.create_collection(
                    "luna_health_sources", metadata={"hnsw:space": "cosine", "fingerprint": fingerprint})
                for b in range(0, len(self.chunks), 256):  # batch to keep memory low on large KBs
                    batch = self.chunks[b:b + 256]
                    # Embed "title: text" so section headings help matching.
                    embs = self.embedder([f"{c['title']}: {c['text']}" for c in batch])
                    self.collection.add(ids=[c["id"] for c in batch], documents=[c["text"] for c in batch],
                                        embeddings=embs,
                                        metadatas=[{"doc_id": c["doc_id"], "title": c["title"], "url": c["url"]} for c in batch])
            self.mode = "semantic embeddings + Chroma"
        except Exception as e:
            log.warning("Semantic index unavailable, using keyword fallback: %s", e)
            self.collection = self.embedder = None
            self.mode = "keyword fallback"
        return {"documents": len(self.docs), "chunks": len(self.chunks), "mode": self.mode}

    def retrieve(self, query, k=5):
        """Return up to k chunks (each with a `score`), filtered by relevance."""
        if self.collection is not None:
            vec = self.embedder([query])
            hits = self.collection.query(query_embeddings=vec, n_results=min(k, len(self.chunks)))
            by_id = {c["id"]: c for c in self.chunks}
            out = []
            for cid, dist in zip(hits["ids"][0], hits["distances"][0]):
                score = 1 - dist  # cosine distance -> similarity
                if cid in by_id and score >= self.min_score:
                    out.append({**by_id[cid], "score": round(score, 4)})
            return out
        terms = set(re.findall(r"[a-z]{3,}", query.lower()))
        scored = []
        for c in self.chunks:
            text = (c["title"] + " " + c["text"] + " " + " ".join(c["keywords"])).lower()
            hit = sum(1 for t in terms if re.search(r"\b" + re.escape(t), text))
            if hit:
                scored.append({**c, "score": round(hit / max(len(terms), 1), 4)})
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:k]


def _numbering(chunks):
    """One citation number per unique source, so [n] in the answer matches the source list."""
    nums = {}
    for c in chunks:
        nums.setdefault(c["url"], len(nums) + 1)
    return nums


def build_prompt(question, chunks):
    nums = _numbering(chunks)
    ctx = "\n".join(f"[{nums[c['url']]}] {c['title']} ({c['url']}): {c['text']}" for c in chunks)
    return PROMPT_TEMPLATE.format(context=ctx, question=question)


GENERAL_PROMPT = (
    "You are Luna, a warm, concise menstrual-health education assistant. Not a diagnostic service. "
    "Luna's trusted source library had nothing on this question, so answer from well-established general medical "
    "knowledge only. Be accurate and cautious: do not give drug doses or diagnoses, say when something is uncertain, "
    "and suggest seeing a clinician when appropriate. If the question is unrelated to health, periods or the body, "
    "politely say you can only help with menstrual and reproductive health. Do not cite sources. "
    "Keep the answer under 180 words.\n\nQuestion: {question}"
)
NOT_IN_SOURCES = ("I couldn't find this in my trusted health sources, so I can't give you a source-backed answer. "
                  "Would you like a general AI answer instead? It won't have citations, so double-check important "
                  "details with a clinician.")
GENERAL_LABEL = "⚠️ *Not found in Luna's trusted sources — this is a general AI answer, so double-check important details with a clinician.*\n\n"


def general_answer(question):
    """Ungrounded answer from the LLM's general knowledge, clearly labelled (same temperature as RAG answers)."""
    return GENERAL_LABEL + generate(GENERAL_PROMPT.format(question=question))


def generate(prompt, retries=5):
    """Call the chat-completions API, retrying on rate limits (429) / temporary 5xx errors."""
    import time, requests
    base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    for attempt in range(retries + 1):
        r = requests.post(base + "/chat/completions",
                          headers={"Authorization": "Bearer " + os.environ["LLM_API_KEY"], "Content-Type": "application/json"},
                          json={"model": os.getenv("LLM_MODEL", "gpt-4o-mini"), "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
                                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]},
                          timeout=35)
        if r.status_code in (429, 500, 502, 503) and attempt < retries:
            wait = float(r.headers.get("Retry-After") or 0) or min(2 ** attempt, 20)
            log.warning("LLM API %s, retrying in %.0fs", r.status_code, wait)
            time.sleep(wait)
            continue
        if not r.ok:  # surface the provider's own message (e.g. "model not found", "invalid api key")
            raise RuntimeError(f"{r.status_code} from {base}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"].strip()


def _sources(chunks):
    titles = {c["url"]: c["title"] for c in chunks}
    return [{"n": n, "title": titles[u], "url": u} for u, n in _numbering(chunks).items()]


def answer_question(question, kb, k=5):
    chunks = kb.retrieve(question, k=k)
    mode = getattr(kb, "mode", "unknown")
    if not chunks:
        # GENERAL_ANSWERS: "ask" (default) = offer an AI answer, "auto" = answer straight away, "off" = never.
        policy = os.getenv("GENERAL_ANSWERS", "ask").lower()
        can = bool(os.getenv("LLM_API_KEY")) and policy != "off"
        if can and policy == "auto":
            return {"answer": general_answer(question), "sources": [], "contexts": [], "retrieval_mode": mode,
                    "grounded": False, "offer_general": False}
        msg = (NOT_IN_SOURCES if can else NO_EVIDENCE)
        return {"answer": msg, "sources": [], "contexts": [], "retrieval_mode": mode,
                "grounded": False, "offer_general": can}
    if not os.getenv("LLM_API_KEY"):
        # Honest local fallback; avoids pretending an LLM was used.
        # Join retrieved chunks without the overlapping sentences, and stop at a sentence boundary.
        seen, sents = set(), []
        for c in chunks[:3]:
            for sent in re.split(r"(?<=[.!?])\s+", c["text"]):
                if sent not in seen and sum(len(x) for x in sents) + len(sent) < 900:
                    seen.add(sent); sents.append(sent)
        answer = ("I'm running without a configured AI provider, so this is a source-based summary rather than a "
                  "generated answer.\n\n" + " ".join(sents) + "\n\nFor a tailored answer, configure LLM_API_KEY in .env.")
    else:
        answer = generate(build_prompt(question, chunks))
    return {"answer": answer, "sources": _sources(chunks), "contexts": [c["text"] for c in chunks],
            "retrieval_mode": mode, "grounded": True, "offer_general": False}
