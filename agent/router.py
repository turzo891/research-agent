import json, shlex
from apscheduler.schedulers.background import BackgroundScheduler
from .tools import web_search, fetch_and_clean, read_pdf, rag_recall

scheduler = BackgroundScheduler()
scheduler.start()

ALLOWED_CMDS = ["dir", "type", "echo", "ipconfig"]  # expand with care

def try_json(msg_text):
    msg_text = msg_text.strip()
    if msg_text.startswith("{") and msg_text.endswith("}"):
        try: return json.loads(msg_text)
        except: return None
    return None

def run_tool(obj):
    t = obj.get("tool"); a = obj.get("args",{})
    if t == "web_search":
        return {"ok": True, "result": web_search(a.get("q",""), a.get("k",5))}
    if t == "web_fetch":
        return {"ok": True, "result": fetch_and_clean(a.get("url",""))}
    if t == "read_pdf":
        return {"ok": True, "result": read_pdf(a.get("path",""), a.get("max_pages",10))}
    if t == "rag_recall":
        return {"ok": True, "result": rag_recall(a.get("query",""), a.get("k",4))}
    if t == "schedule":
        scheduler.add_job(lambda: print(f"[TASK] {a.get('title','Task')}: {a.get('note','')}"),
                          'date', run_date=a.get("when"))
        return {"ok": True, "result": f"Scheduled {a.get('title','Task')} at {a.get('when')}"}
    if t == "shell":
        cmd = a.get("command","")
        if not cmd: return {"ok": False, "error":"Missing command"}
        exe = shlex.split(cmd)[0].lower()
        if exe not in ALLOWED_CMDS:
            return {"ok": False, "error":"Command not allowed"}
        # We don't run it here—ask user to confirm first.
        return {"ok": True, "result": f"[CONFIRM_REQUIRED] {cmd}"}
    return {"ok": False, "error":"Unknown tool"}
