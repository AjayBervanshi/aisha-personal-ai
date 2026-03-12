import os
import sys
import argparse
import re
from datetime import datetime
from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(".env")

from src.core.ai_router import AIRouter
from supabase import create_client

def parse_whatsapp(filepath: str, your_name: str, her_name: str = "Aisha"):
    """
    Parses WhatsApp exported .txt format:
    [DD/MM/YY, HH:MM:SS] Name: Message
    Returns a list of dictionaries grouped by date.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    chunks_by_day = {}
    
    # regex for WhatsApp format: [12/10/24, 09:41:22] Name: Message
    pattern = re.compile(r'\[?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]?\s*(.*?):\s*(.*)')
    
    for line in lines:
        match = pattern.search(line)
        if match:
            date_str, time_str, sender, message = match.groups()
            
            # Map names if provided
            if your_name.lower() in sender.lower() or "you" in sender.lower():
                sender = "Ajay"
            elif her_name.lower() in sender.lower():
                sender = "Aisha"
                
            if message.strip() == "" or "<Media omitted>" in message or "omitted" in message:
                continue
                
            if date_str not in chunks_by_day:
                chunks_by_day[date_str] = []
                
            chunks_by_day[date_str].append(f"[{time_str}] {sender}: {message.strip()}")

    return chunks_by_day

def process_and_store(chunks: dict):
    """
    Takes daily chunks of conversations, sends them to AI for memory extraction,
    and stores the resulting insights into Supabase.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    db = create_client(supabase_url, supabase_key)
    
    router = AIRouter()
    
    total_days = len(chunks)
    print(f"Found {total_days} days of conversation history.")
    
    for idx, (date_str, messages) in enumerate(chunks.items(), 1):
        if len(messages) < 3:
            continue # Skip days with barely any chat
            
        print(f"\n[{idx}/{total_days}] Processing {date_str} ({len(messages)} messages)...")
        chat_text = "\n".join(messages)
        
        # We don't want to process 5000 lines at once for a single day. 
        # Cap at last 200 messages for the day to avoid token limits, or chunk further.
        if len(messages) > 150:
            chat_text = "\n".join(messages[-150:])
            
        prompt = f"""
        Analyze this historical daily chat log between Ajay and Aisha from {date_str}.
        
        Chat Log:
        {chat_text}
        
        Extract ONLY the most critical, timeless, long-term facts about Ajay (his preferences, life events, deep insecurities, goals, facts about his life). DO NOT extract trivial small talk or temporary moods.
        
        If there are important facts, return them as a strictly valid JSON array of objects:
        [
            {{
                "category": "preference" | "goal" | "event" | "finance" | "other",
                "title": "Short descriptive title",
                "content": "Detailed fact learned",
                "importance": 1-5,
                "tags": ["relevant", "tags"]
            }}
        ]
        
        If NOTHING important is found, return exactly this string: "[]"
        Return ONLY valid JSON. Keep it robust.
        """
        
        # Use Claude, Groq, or Gemini to parse
        result = router.generate("You are an expert data parser extracting JSON.", prompt)
        
        # Clean JSON
        json_str = result.text
        match = re.search(r'\[.*\]', json_str, re.DOTALL)
        if match:
            try:
                import json
                extracted_memories = json.loads(match.group(0))
                for mem in extracted_memories:
                    # Insert to Supabase manually
                    mem_data = {
                        "category": mem.get("category", "other"),
                        "title": f"[History: {date_str}] {mem.get('title', 'Memory')}",
                        "content": mem.get("content", ""),
                        "importance": mem.get("importance", 3),
                        "tags": mem.get("tags", ["history"]),
                        "is_active": True
                    }
                    db.table("aisha_memory").insert(mem_data).execute()
                    print(f"  ✅ Saved Fact: {mem_data['title']}")
            except json.JSONDecodeError:
                print(f"  ❌ Failed to parse JSON for {date_str}")
                print(f"      Raw output: {json_str[:200]}")
        else:
            print("  ℹ️ No critical facts extracted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest historical chat data for Aisha's brain.")
    parser.add_argument("file", help="Path to the exported .txt chat log")
    parser.add_argument("--your_name", required=True, help="Your exact contact name in the export file")
    parser.add_argument("--her_name", default="Aisha", help="Her exact contact name in the export file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found!")
        sys.exit(1)
        
    print(f"Loading {args.file}...")
    chunks = parse_whatsapp(args.file, args.your_name, args.her_name)
    process_and_store(chunks)
    
    print("\n✅ Deep Learning complete! Aisha now remembers this past life.")
