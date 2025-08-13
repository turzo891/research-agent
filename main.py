import asyncio
from agent.voice import speak

import json, re, sys
from agent.tools import fetch_and_clean, web_search
from agent.router import try_json, run_tool
from agent.workflow import FIRST_MESSAGE, step_1_2_3, step_4, step_5_6_7

def ask_first():
    print(FIRST_MESSAGE)
    print("Paste your brief (end with a blank line):\n")
    buf=[]
    while True:
        try: line = input()
        except EOFError: break
        if not line.strip(): break
        buf.append(line)
    return "\n".join(buf).strip()

def compactify(results, limit=20, max_excerpt=1200):
    compact = []
    for r in results[:limit]:
        if isinstance(r, dict) and r.get("url"):
            compact.append({
                "query": r.get("query",""),
                "title": r.get("title",""),
                "url": r.get("url",""),
                "excerpt": (r.get("text") or r.get("snippet") or "")[:max_excerpt]
            })
    return json.dumps(compact, ensure_ascii=False)

if __name__ == "__main__":
    print("== J.A.R.V.I.S. Research Assistant (Windows) ==")
    user_brief = ask_first()

    # (1)-(2)-(3)
    outline = step_1_2_3(user_brief)
    print("\n=== (1)-(2)-(3): Refined question, Outline, Search queries ===\n")
    print(outline)

    # Extract queries (simple heuristic: bullet list lines start with "- ")
    queries = re.findall(r"- (.+?)(?:\n|$)", outline)
    queries = [q.strip() for q in queries][:6]
    print("\n[INFO] Web queries:", queries)

    # Run search+fetch
    research_pack = []
    for q in queries:
        hits = web_search(q, k=6)
        for h in hits:
            text = fetch_and_clean(h["url"])
            research_pack.append({"query": q, "title": h["title"], "url": h["url"], "text": text, "snippet": h["snippet"]})

    # (4) Source summaries
    compact = compactify(research_pack)
    summaries = step_4(user_brief, compact)
    print("\n=== (4): Source summaries (with links/DOIs) ===\n")
    print(summaries)

    # (5)-(6)-(7) Draft
    draft = step_5_6_7(user_brief, outline, summaries)
    print("\n=== (5)-(6)-(7): Draft, Provisional bibliography, Limitations & Next Checks ===\n")
    print(draft)

    print("\nDone.")
