import asyncio
import json, re
from agent.voice import speak
from agent.tools import fetch_and_clean, web_search
from agent.router import try_json, run_tool
from agent.workflow import FIRST_MESSAGE, step_1_2_3, step_4, step_5_6_7

def ask_first():
    print(FIRST_MESSAGE)
    print("Paste your brief (end with a blank line):\n")
    buf = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        buf.append(line)
    return "\n".join(buf).strip()

def compactify(results, limit=20, max_excerpt=1200):
    compact = []
    for r in results[:limit]:
        if isinstance(r, dict) and r.get("url"):
            compact.append({
                "query": r.get("query", ""),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "excerpt": (r.get("text") or r.get("snippet") or "")[:max_excerpt]
            })
    return json.dumps(compact, ensure_ascii=False)

def extract_queries(outline_text, max_q=8):
    # Prefer a “Targeted Search Queries” block if present
    block = outline_text
    m = re.search(r"(Targeted Search Queries.*?)(?:\n\n|\Z)", outline_text, flags=re.I | re.S)
    if m:
        block = m.group(1)

    candidates = []
    for line in block.splitlines():
        line = line.strip(" \t•*-–")
        if not line:
            continue
        # strip list numbers like "1. " or "2) "
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        # treat likely query lines
        if any(tok in line for tok in [" AND ", " OR ", "\"", "carbon", "emission", "pricing", "regulation", "OECD"]):
            if len(line.split()) >= 3 and not line.lower().startswith(("academic databases", "search queries")):
                candidates.append(line)

    # Fallback: catch markdown bullets if nothing found
    if not candidates:
        candidates = [m.group(1).strip() for m in re.finditer(r"^[\-\*]\s+(.*)$", outline_text, flags=re.M)]

    # unique + cap
    seen, out = set(), []
    for q in candidates:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q.lower() not in seen:
            out.append(q)
            seen.add(q.lower())
        if len(out) >= max_q:
            break
    return out

if __name__ == "__main__":
    print("== F.O.R.R.E.S.T. Research Assistant (Windows) ==")
    user_brief = ask_first()

    if not user_brief.strip():
        print("No brief provided. Please paste the 7 items (topic, audience, length, style, constraints, stance, required sources).")
        asyncio.run(speak("I didn't receive a brief. Please paste the seven items."))
        raise SystemExit(1)

    asyncio.run(speak("Got your brief. Generating outline and search queries."))

    # (1)-(2)-(3)
    outline = step_1_2_3(user_brief)
    print("\n=== (1)-(2)-(3): Refined question, Outline, Search queries ===\n")
    print(outline)

    # Extract queries (robust)
    queries = extract_queries(outline)
    print("\n[INFO] Web queries:", queries)
    if not queries:
        print("[WARN] No queries found in the outline. Using safe defaults.")
        queries = [
            '("carbon pricing" OR "carbon tax") AND ("emission reduction" OR "GHG") AND OECD AND 2015..2025',
            '("cap-and-trade" OR ETS OR "emissions trading system") AND ("difference-in-differences" OR DID) OECD',
            '"command-and-control" regulation climate policy empirical OECD',
            '"sectoral standards" carbon pricing interaction empirical',
            '"World Bank" "Carbon Pricing Dashboard" OECD 2015..2025'
        ]

    # Run search+fetch
    research_pack = []
    for q in queries:
        hits = web_search(q, k=6)
        for h in hits:
            text = fetch_and_clean(h["url"])
            research_pack.append({
                "query": q,
                "title": h["title"],
                "url": h["url"],
                "text": text,
                "snippet": h.get("content") or h.get("snippet")
            })

    # (4) Source summaries
    asyncio.run(speak("Summarizing sources from the web."))
    compact = compactify(research_pack)
    summaries = step_4(user_brief, compact)
    print("\n=== (4): Source summaries (with links/DOIs) ===\n")
    print(summaries)

    # (5)-(6)-(7) Draft
    draft = step_5_6_7(user_brief, outline, summaries)
    print("\n=== (5)-(6)-(7): Draft, Provisional bibliography, Limitations & Next Checks ===\n")
    print(draft)

    asyncio.run(speak("Draft complete. I included limitations and next checks."))
    print("\nDone.")
