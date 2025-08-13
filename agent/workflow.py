import os, json, re
from .tools import llm_chat, enforce_marks

POLICY = open("policy.txt", "r", encoding="utf-8").read()

FIRST_MESSAGE = """To begin, please provide:
1) Topic & research question
2) Course/venue and audience
3) Target length and deadline
4) Citation style (APA/MLA/Chicago/IEEE/etc.)
5) Constraints (regions/years/methods)
6) Stance or hypotheses
7) Any required sources or datasets
"""

def step_1_2_3(user_brief):
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"User brief:\n{user_brief}\n\nProduce sections (1)-(2)-(3) only: refined question & scope, outline, and targeted search queries & databases."}
    ]
    return llm_chat(msgs)

def step_4(user_brief, compact_results_json):
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"""User brief:
{user_brief}

Summarize credible sources with links/DOIs (Section 4).
Use only what appears in the provided results—no fabrication.
If unsure, mark [VERIFY].

Results:
{compact_results_json[:120000]}
"""}
    ]
    return llm_chat(msgs)

def step_5_6_7(user_brief, outline_text, source_summaries):
    msgs = [
        {"role":"system","content":POLICY},
        {"role":"user","content":f"""User brief:
{user_brief}

Draft Sections (5) Draft sections with in-text citations, (6) Provisional bibliography, and (7) Limitations & Next Checks.
Rules:
- Insert in-text citations only if a URL/DOI is present in the summaries.
- Quote ≤40 words with quotation marks and page numbers if available; otherwise paraphrase with attribution.
- Mark uncertain claims [VERIFY] and missing references [CITE].

Outline:
{outline_text}

Source summaries:
{source_summaries}
"""}
    ]
    return enforce_marks(llm_chat(msgs))
