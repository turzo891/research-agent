import os, re, json, time, requests
from readability import Document
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
TAVILY_KEY   = os.getenv("TAVILY_API_KEY")

# ----- LLM -----
def llm_chat(messages, temperature=0.2):
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False
    }, timeout=180)
    resp.raise_for_status()
    return resp.json()["message"]["content"]

# ----- Web search & fetch -----
def web_search(q, k=5):
    if not TAVILY_KEY:
        return []
    r = requests.post("https://api.tavily.com/search", json={
        "api_key": TAVILY_KEY, "query": q, "max_results": k
    }, timeout=60)
    r.raise_for_status()
    data = r.json().get("results", [])
    return [{"title": i.get("title"), "url": i.get("url"), "snippet": i.get("content")} for i in data]

def fetch_and_clean(url, max_chars=20000):
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        ct = r.headers.get("Content-Type","")
        if "text/html" in ct:
            doc = Document(r.text)
            html = doc.summary()
            text = BeautifulSoup(html, "html.parser").get_text("\n")
        else:
            text = r.text
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars]
    except Exception as e:
        return f"[ERROR fetching {url}: {e}]"

# ----- PDF read (page text with page numbers) -----
def read_pdf(path, max_pages=10):
    out = []
    try:
        reader = PdfReader(path)
        pages = min(len(reader.pages), max_pages)
        for i in range(pages):
            out.append({"page": i+1, "text": reader.pages[i].extract_text() or ""})
    except Exception as e:
        return [{"page": 0, "text": f"[ERROR reading PDF: {e}]"}]
    return out

# ----- Simple citation checks -----
def url_ok(url):
    try:
        h = requests.head(url, allow_redirects=True, timeout=20)
        return 200 <= h.status_code < 400
    except Exception:
        return False

# ----- Memory (RAG) -----
_model = None
_chroma = None
def get_embedder():
    global _model; 
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def get_chroma():
    global _chroma
    if _chroma is None:
        _chroma = chromadb.Client()
    return _chroma

def index_folder(folder="data/user_docs"):
    coll = get_chroma().get_or_create_collection("jarvis_mem")
    embedder = get_embedder()
    docs = []
    for root, _, files in os.walk(folder):
        for f in files:
            path = os.path.join(root, f)
            text = ""
            if f.lower().endswith(".pdf"):
                parts = read_pdf(path, max_pages=30)
                text = "\n\n".join([p["text"] for p in parts])
            elif f.lower().endswith((".txt", ".md")):
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            # (optional) add docx handling
            if text.strip():
                emb = embedder.encode(text).tolist()
                coll.add(documents=[text], embeddings=[emb], metadatas=[{"path": path}], ids=[path])
    return "Indexed."

def rag_recall(query, k=4):
    coll = get_chroma().get_or_create_collection("jarvis_mem")
    emb = get_embedder().encode(query).tolist()
    res = coll.query(query_embeddings=[emb], n_results=k)
    items = []
    for doc, meta in zip(res.get("documents",[[]])[0], res.get("metadatas",[[]])[0]):
        items.append({"path": meta.get("path"), "text": doc[:1200]})
    return items

# ----- Utility: add [CITE] to naked year claims -----
def enforce_marks(text):
    lines = []
    for line in text.splitlines():
        if re.search(r"\b\d{4}\b", line) and not re.search(r"\([^)]+,\s*\d{4}\)", line):
            line += " [CITE]"
        lines.append(line)
    return "\n".join(lines)
