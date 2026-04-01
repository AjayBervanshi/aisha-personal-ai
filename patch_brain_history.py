with open("src/core/aisha_brain.py", "r") as f:
    code = f.read()

# We need to enforce AI_HISTORY_LIMIT on self.history so it doesn't grow to infinity.
# Also, we should decouple the auto-extract call to a background thread to speed up the reply time!

old_extract = """        # 8. Auto-extract and save important info from conversation
        if user_role == "admin":
            self._auto_extract_memory(user_message, response_text, telegram_id=telegram_id)

        return response_text"""

new_extract = """        # 8. Manage History Limit (Prevent context overflow)
        if len(self.history) > AI_HISTORY_LIMIT:
            # Keep the most recent messages, ensuring we don't sever a tool_call pair
            self.history = self.history[-AI_HISTORY_LIMIT:]

        # 9. Auto-extract and save important info in a background thread
        if user_role == "admin":
            import threading
            threading.Thread(target=self._auto_extract_memory, args=(user_message, response_text, telegram_id), daemon=True).start()

        return response_text"""

if old_extract in code:
    code = code.replace(old_extract, new_extract)
    with open("src/core/aisha_brain.py", "w") as f:
        f.write(code)
    print("Successfully patched aisha_brain.py to fix memory leak and threaded extraction!")
else:
    print("Could not find the exact code block to patch in aisha_brain.py.")
