import os, json, textwrap, re, time
from dotenv import load_dotenv
import requests
from readability import Document
from bs4 import BeautifulSoup

# ---------- Config ----------
load_dotenv()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
TAVILY_KEY   = os.environ.get("TAVILY_API_KEY")

def ollama_chat(messages, temperature=0.2):
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]

# ---------- Web search + fetch ----------
def tavily_search(q, max_results=5):
    if not TAVILY_KEY:
        return []
    r = requests.post("https://api.tavily.com/search", json={
        "api_key": TAVILY_KEY, "query": q, "max_results": max_results
    }, timeout=60)
    r.raise_for_status()
    data = r.json()
    return [{"title": i.get("title"), "url": i.get("url"), "snippet": i.get("content")} for i in data.get("results", [])]

def fetch_and_clean(url, max_chars=20000):
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        if "text/html" in r.headers.get("Content-Type",""):
            doc = Document(r.text)
            html = doc.summary()
            text = BeautifulSoup(html, "html.parser").get_text("\n")
        else:
            text = r.text
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars]
    except Exception as e:
        return f"[ERROR fetching {url}: {e}]"

# ---------- Policy helpers ----------
with open("policy.txt", "r", encoding="utf-8") as f:
    POLICY = f.read()

def enforce_marks(text):
    lines = []
    for line in text.splitlines():
        if re.search(r"\b\d{4}\b", line) and not re.search(r"\([^)]+,\s*\d{4}\)", line):
            line += " [CITE]"
        lines.append(line)
    return "\n".join(lines)

# ---------- Agent steps ----------
def first_message():
    return textwrap.dedent("""\
        To begin, please provide:
        1) Topic & research question
        2) Course/venue and audience
        3) Target length and deadline
        4) Citation style (APA/MLA/Chicago/IEEE/etc.)
        5) Constraints (regions/years/methods)
        6) Stance or hypotheses
        7) Any required sources or datasets
    """)

def propose_outline(user_brief):
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"User brief:\n{user_brief}\n\nProduce sections (1)-(2)-(3) only: refined question & scope, outline, and targeted search queries."}
    ]
    return ollama_chat(msgs)

def web_research(queries):
    bundle = []
    for q in queries:
        hits = tavily_search(q, max_results=6) if TAVILY_KEY else []
        for h in hits:
            body = fetch_and_clean(h["url"])
            bundle.append({"query": q, "title": h["title"], "url": h["url"], "snippet": h["snippet"], "text": body})
            time.sleep(0.3)
    return bundle

def summarize_sources(user_brief, research_pack):
    compact = []
    for r in research_pack[:20]:
        compact.append({
            "query": r["query"],
            "title": r["title"],
            "url": r["url"],
            "excerpt": r["text"][:1200]
        })
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"User brief:\n{user_brief}\n\nSummarize credible sources with links/DOIs. Only use what is actually present. If unsure, mark [VERIFY].\n\nResults:\n{json.dumps(compact, ensure_ascii=False)[:120000]}"}
    ]
    return ollama_chat(msgs)

def draft_sections(user_brief, outline_text, source_summaries):
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"""User brief:
{user_brief}

Use the outline and source summaries to draft sections (5), (6), and (7).
- Insert in-text citations only if the URL/DOI is present in the summaries.
- Quote ≤40 words with quotation marks and page numbers if provided; else paraphrase and attribute.
- Mark uncertain claims as [VERIFY]; missing references as [CITE].
Outline:
{outline_text}

Source summaries:
{source_summaries}
"""}
    ]
    draft = ollama_chat(msgs)
    return enforce_marks(draft)

if __name__ == "__main__":
    print("Research Agent (Ollama) - Windows")
    print(first_message())
    print("\nPaste your brief, end with a blank line:\n")
    buf = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        buf.append(line)
    user_brief = "\n".join(buf).strip()

    outline = propose_outline(user_brief)
    print("\n=== (1)-(2)-(3): Refined question, Outline, Search queries ===\n")
    print(outline)

    queries = re.findall(r"- (.+?)(?:\n|$)", outline)[:6]
    print("\n[INFO] Using queries:", queries, "\n")

    pack = web_research(queries)
    summaries = summarize_sources(user_brief, pack)
    print("\n=== (4): Source summaries (with links/DOIs) ===\n")
    print(summaries)

    draft = draft_sections(user_brief, outline, summaries)
    print("\n=== (5)-(6)-(7): Draft, Provisional bibliography, Limitations & Next Checks ===\n")
    print(draft)
