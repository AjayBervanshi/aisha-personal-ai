import re

with open("src/core/digest_engine.py", "r") as f:
    content = f.read()

search = """            # Tasks
            tasks_done = (db.table("aisha_schedule").select("id")
                          .eq("due_date", today).eq("status", "done").execute()).data or []
            tasks_missed = (db.table("aisha_schedule").select("id")
                            .eq("due_date", today).eq("status", "missed").execute()).data or []
            tasks_pending = (db.table("aisha_schedule").select("title")
                             .eq("due_date", today).eq("status", "pending").execute()).data or []
            stats["tasks_done"] = len(tasks_done)
            stats["tasks_missed"] = len(tasks_missed)
            stats["tasks_pending"] = [t["title"] for t in tasks_pending]"""

replace = """            # Tasks
            # Optimization: Fetch all task statuses for today in one query
            all_tasks = (db.table("aisha_schedule").select("id, title, status")
                         .eq("due_date", today).in_("status", ["done", "missed", "pending"]).execute()).data or []

            tasks_done = [t for t in all_tasks if t.get("status") == "done"]
            tasks_missed = [t for t in all_tasks if t.get("status") == "missed"]
            tasks_pending = [t for t in all_tasks if t.get("status") == "pending"]

            stats["tasks_done"] = len(tasks_done)
            stats["tasks_missed"] = len(tasks_missed)
            stats["tasks_pending"] = [t["title"] for t in tasks_pending]"""

if search in content:
    with open("src/core/digest_engine.py", "w") as f:
        f.write(content.replace(search, replace))
    print("Patched successfully")
else:
    print("Search string not found")
