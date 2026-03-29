"""
import_history.py
================
Import your chat history from Claude, ChatGPT, Gemini & Grok into Aisha's memory.

Usage:
  python scripts/import_history.py --source chatgpt  --file path/to/conversations.json
  python scripts/import_history.py --source claude   --file path/to/claude_export.zip
  python scripts/import_history.py --source gemini   --file path/to/Takeout.zip
  python scripts/import_history.py --source grok     --file path/to/data.zip
  python scripts/import_history.py --all             --dir  path/to/exports/folder/

How to export your data:
  Claude   → claude.ai → Profile → Settings → Export data
  ChatGPT  → chatgpt.com → Profile → Settings → Data Controls → Export data
  Gemini   → takeout.google.com → Select "Gemini Apps Activity"
  Grok     → x.com → Settings → Your account → Download archive of data
"""

import os
import sys
import json

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import zipfile
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()


# ── Stats tracker ─────────────────────────────────────────────
stats = {"processed": 0, "memories_saved": 0, "skipped": 0}


# ══════════════════════════════════════════════════════════════
# PARSERS — one per platform
# ══════════════════════════════════════════════════════════════

def parse_chatgpt(filepath: str) -> List[Dict]:
    """Parse ChatGPT export (conversations.json)."""
    print(f"\n📂 Parsing ChatGPT export: {filepath}")
    conversations = []
    path = Path(filepath)

    # Handle zip or direct JSON
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            conv_file = next((n for n in names if "conversations.json" in n), None)
            if not conv_file:
                print("  ❌ conversations.json not found in zip!")
                return []
            data = json.loads(z.read(conv_file))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))

    for convo in data:
        title = convo.get("title", "Untitled")
        messages = []
        mapping = convo.get("mapping", {})
        for node in mapping.values():
            msg = node.get("message")
            if not msg:
                continue
            role = msg.get("author", {}).get("role", "")
            content = msg.get("content", {})
            parts = content.get("parts", [])
            text = " ".join(str(p) for p in parts if isinstance(p, str))
            if text and role in ("user", "assistant"):
                messages.append({"role": role, "text": text})

        if messages:
            conversations.append({"source": "chatgpt", "title": title, "messages": messages})

    print(f"  ✅ Found {len(conversations)} ChatGPT conversations")
    return conversations


def parse_claude(filepath: str) -> List[Dict]:
    """Parse Claude export (ZIP with JSON files)."""
    print(f"\n📂 Parsing Claude export: {filepath}")
    conversations = []
    path = Path(filepath)

    files_to_parse = []
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith(".json"):
                    try:
                        data = json.loads(z.read(name))
                        files_to_parse.append(data)
                    except Exception:
                        pass
    elif path.suffix == ".json":
        files_to_parse.append(json.loads(path.read_text(encoding="utf-8")))

    for data in files_to_parse:
        # Claude export format
        if isinstance(data, list):
            for convo in data:
                msgs = []
                for msg in convo.get("messages", []):
                    role = "user" if msg.get("sender") == "human" else "assistant"
                    text = msg.get("text", "")
                    if text:
                        msgs.append({"role": role, "text": text})
                if msgs:
                    conversations.append({
                        "source": "claude",
                        "title": convo.get("name", "Claude conversation"),
                        "messages": msgs
                    })
        elif isinstance(data, dict):
            msgs = []
            for msg in data.get("messages", []):
                role = "user" if msg.get("role") in ("human", "user") else "assistant"
                text = msg.get("content", "") or msg.get("text", "")
                if text:
                    msgs.append({"role": role, "text": text})
            if msgs:
                conversations.append({
                    "source": "claude",
                    "title": data.get("name", "Claude conversation"),
                    "messages": msgs
                })

    print(f"  ✅ Found {len(conversations)} Claude conversations")
    return conversations


def parse_gemini(filepath: str) -> List[Dict]:
    """Parse Google Takeout Gemini export."""
    print(f"\n📂 Parsing Gemini export: {filepath}")
    conversations = []
    path = Path(filepath)

    text_blocks = []
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if "Gemini" in name and name.endswith(".json"):
                    try:
                        data = json.loads(z.read(name))
                        text_blocks.append(data)
                    except Exception:
                        pass
                elif "Gemini" in name and name.endswith(".html"):
                    try:
                        html = z.read(name).decode("utf-8", errors="ignore")
                        text_blocks.append({"_html": html, "_filename": name})
                    except Exception:
                        pass

    for block in text_blocks:
        if "_html" in block:
            # Parse HTML format
            html = block["_html"]
            user_msgs = re.findall(r'<div class="user-message"[^>]*>(.*?)</div>', html, re.DOTALL)
            ai_msgs   = re.findall(r'<div class="model-response"[^>]*>(.*?)</div>', html, re.DOTALL)
            msgs = []
            for u, a in zip(user_msgs, ai_msgs):
                u_clean = re.sub('<[^<]+?>', '', u).strip()
                a_clean = re.sub('<[^<]+?>', '', a).strip()
                if u_clean: msgs.append({"role": "user", "text": u_clean})
                if a_clean: msgs.append({"role": "assistant", "text": a_clean})
            if msgs:
                conversations.append({"source": "gemini", "title": block["_filename"], "messages": msgs})
        elif isinstance(block, list):
            for item in block:
                msgs = []
                for turn in item.get("conversation", []):
                    role = "user" if turn.get("role") == "user" else "assistant"
                    text = turn.get("parts", [{}])[0].get("text", "")
                    if text:
                        msgs.append({"role": role, "text": text})
                if msgs:
                    conversations.append({"source": "gemini", "title": "Gemini chat", "messages": msgs})

    print(f"  ✅ Found {len(conversations)} Gemini conversations")
    return conversations


def parse_grok(filepath: str) -> List[Dict]:
    """Parse Grok/X archive export."""
    print(f"\n📂 Parsing Grok export: {filepath}")
    conversations = []
    path = Path(filepath)

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if "grok" in name.lower() and name.endswith(".json"):
                    try:
                        data = json.loads(z.read(name))
                        for convo in (data if isinstance(data, list) else [data]):
                            msgs = []
                            for msg in convo.get("messages", []):
                                role = "user" if msg.get("role") == "user" else "assistant"
                                text = msg.get("content", "")
                                if text:
                                    msgs.append({"role": role, "text": text})
                            if msgs:
                                conversations.append({
                                    "source": "grok",
                                    "title": convo.get("title", "Grok conversation"),
                                    "messages": msgs
                                })
                    except Exception:
                        pass

    print(f"  ✅ Found {len(conversations)} Grok conversations")
    return conversations


# ══════════════════════════════════════════════════════════════
# MEMORY EXTRACTOR
# ══════════════════════════════════════════════════════════════

def extract_memories(conversations: List[Dict]) -> List[Dict]:
    """
    Extract meaningful memories from conversations.
    Looks for: goals, preferences, feelings, facts about Ajay, financial info.
    """
    memories = []

    GOAL_PATTERNS = [
        r"(?:my goal|i want to|i plan to|i'm planning|i aim to|dream is|want to become|trying to)(.{10,150})",
    ]
    PREFERENCE_PATTERNS = [
        r"(?:i love|i like|i enjoy|i prefer|my favourite|my favorite|i hate|i dislike)(.{5,100})",
    ]
    FINANCE_PATTERNS = [
        r"(?:my salary|i earn|i make|i spend|my budget|i save|my income|i owe|i have ₹|i have rs)(.{5,100})",
    ]
    PERSONAL_PATTERNS = [
        r"(?:i am|i'm a|i work as|my job is|i study|i live in|my age|i was born)(.{5,100})",
    ]

    pattern_groups = [
        ("goal",       GOAL_PATTERNS,       4),
        ("preference", PREFERENCE_PATTERNS, 3),
        ("finance",    FINANCE_PATTERNS,    4),
        ("personal",   PERSONAL_PATTERNS,   4),
    ]

    for convo in conversations:
        source = convo["source"]
        title  = convo["title"]
        for msg in convo["messages"]:
            if msg["role"] != "user":
                continue
            text = msg["text"].lower()

            for category, patterns, importance in pattern_groups:
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        clean = match.strip()[:200]
                        if len(clean) > 15:
                            memories.append({
                                "category":   category,
                                "title":      f"From {source}: {clean[:60]}...",
                                "content":    f"[{source.upper()} import] Ajay said: {clean}",
                                "importance": importance,
                                "tags":       [source, "imported", category],
                                "source":     f"{source}_import"
                            })

    # Deduplicate by content similarity
    seen = set()
    unique = []
    for m in memories:
        key = m["content"][:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique


# ══════════════════════════════════════════════════════════════
# SUPABASE SAVER
# ══════════════════════════════════════════════════════════════

def save_to_supabase(memories: List[Dict]) -> int:
    """Save extracted memories to Supabase."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key or "your_" in url:
            print("\n⚠️  Supabase not configured — saving to local file instead.")
            return save_to_file(memories)

        db = create_client(url, key)
        saved = 0
        for mem in memories:
            try:
                db.table("aisha_memory").insert(mem).execute()
                saved += 1
            except Exception as e:
                print(f"  ⚠️  Could not save: {mem['title'][:50]} — {e}")

        return saved

    except ImportError:
        print("  ⚠️  supabase not installed — saving to file.")
        return save_to_file(memories)


def save_to_file(memories: List[Dict]) -> int:
    """Save memories to local JSON file as fallback."""
    out = Path(__file__).parent.parent / "data" / "imported_memories.json"
    out.parent.mkdir(exist_ok=True)

    existing = []
    if out.exists():
        existing = json.loads(out.read_text())

    existing.extend(memories)
    out.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"  💾 Saved to {out}")
    return len(memories)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Import AI chat history into Aisha")
    parser.add_argument("--source", choices=["chatgpt", "claude", "gemini", "grok"])
    parser.add_argument("--file",  help="Path to your export file/zip")
    parser.add_argument("--all",   action="store_true", help="Import all from --dir")
    parser.add_argument("--dir",   help="Folder containing all export files")
    parser.add_argument("--dry-run", action="store_true", help="Don't save, just preview")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("🧠 AISHA — Chat History Import Tool")
    print("="*55)

    all_conversations = []

    if args.all and args.dir:
        # Auto-detect all exports in a folder
        folder = Path(args.dir)
        for file in folder.iterdir():
            name = file.name.lower()
            if "chatgpt" in name or "conversations" in name:
                all_conversations.extend(parse_chatgpt(str(file)))
            elif "claude" in name:
                all_conversations.extend(parse_claude(str(file)))
            elif "gemini" in name or "takeout" in name:
                all_conversations.extend(parse_gemini(str(file)))
            elif "grok" in name or "twitter" in name or "x-" in name:
                all_conversations.extend(parse_grok(str(file)))

    elif args.source and args.file:
        parsers = {
            "chatgpt": parse_chatgpt,
            "claude":  parse_claude,
            "gemini":  parse_gemini,
            "grok":    parse_grok,
        }
        all_conversations = parsers[args.source](args.file)
    else:
        parser.print_help()
        sys.exit(1)

    print(f"\n📊 Total conversations loaded: {len(all_conversations)}")

    # Extract memories
    print("\n🔍 Extracting memories from conversations...")
    memories = extract_memories(all_conversations)
    print(f"  Found {len(memories)} meaningful memories to import")

    if args.dry_run:
        print("\n🔬 DRY RUN — Preview of memories to be saved:")
        for m in memories[:10]:
            print(f"  [{m['category'].upper()}] {m['title']}")
        if len(memories) > 10:
            print(f"  ... and {len(memories) - 10} more")
        print("\nRun without --dry-run to actually save.")
        return

    # Save
    print("\n💾 Saving memories to Aisha's brain...")
    saved = save_to_supabase(memories)

    print(f"\n{'='*55}")
    print(f"✅ Import complete!")
    print(f"   Conversations processed: {len(all_conversations)}")
    print(f"   Memories extracted:      {len(memories)}")
    print(f"   Memories saved:          {saved}")
    print(f"\nAisha now knows your history 💜")
    print("="*55)


if __name__ == "__main__":
    main()
