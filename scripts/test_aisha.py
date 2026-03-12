"""
test_aisha.py
=============
Quick local test to verify Aisha is working before deployment.
Run: python scripts/test_aisha.py
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def test_env_vars():
    """Check all required environment variables are set."""
    print("\n🔑 Checking environment variables...")
    required = ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    optional = ["GROQ_API_KEY", "TELEGRAM_BOT_TOKEN", "ELEVENLABS_API_KEY"]
    
    all_good = True
    for var in required:
        val = os.getenv(var)
        if val and val != f"your_{var.lower()}_here":
            print(f"  ✅ {var} — set")
        else:
            print(f"  ❌ {var} — MISSING! Add to your .env file")
            all_good = False
    
    for var in optional:
        val = os.getenv(var)
        if val and "your_" not in val:
            print(f"  ✅ {var} — set (optional)")
        else:
            print(f"  ⚠️  {var} — not set (optional)")
    
    return all_good

def test_gemini():
    """Test Gemini API connection."""
    print("\n🧠 Testing Gemini API...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'Aisha is working!' in exactly those words.")
        if "Aisha" in response.text:
            print("  ✅ Gemini API — working!")
            return True
        else:
            print(f"  ⚠️  Gemini responded but unexpected: {response.text[:100]}")
            return True
    except Exception as e:
        print(f"  ❌ Gemini error: {e}")
        return False

def test_supabase():
    """Test Supabase connection."""
    print("\n🗄️  Testing Supabase...")
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        result = sb.table("ajay_profile").select("name").limit(1).execute()
        if result.data:
            print(f"  ✅ Supabase — connected! Profile found: {result.data[0].get('name', 'Unknown')}")
        else:
            print("  ⚠️  Supabase connected but profile table empty — run seed.sql!")
        return True
    except Exception as e:
        print(f"  ❌ Supabase error: {e}")
        return False

def run_chat_test():
    """Interactive test — chat with Aisha."""
    print("\n💜 Starting Aisha chat test...")
    print("=" * 50)
    
    try:
        from src.core.aisha_brain import AishaBrain
        aisha = AishaBrain()
        
        # Test messages
        test_messages = [
            "Hey Aisha!",
            "Mujhe aaj motivate karo!",  # Hindi
            "माझ्या goal बद्दल बोलूया",    # Marathi
        ]
        
        for msg in test_messages:
            print(f"\nYou: {msg}")
            response = aisha.think(msg)
            print(f"Aisha: {response[:200]}{'...' if len(response) > 200 else ''}")
        
        print("\n" + "=" * 50)
        print("✅ Chat test complete!")
        print("\n🎉 Aisha is fully working! You can now:")
        print("   → Run the Telegram bot: python src/telegram/bot.py")
        print("   → Open the web app: src/web/index.html")
        
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        import traceback; traceback.print_exc()

def interactive_mode():
    """Full interactive chat mode."""
    try:
        from src.core.aisha_brain import AishaBrain
        aisha = AishaBrain()
        
        print("\n" + "="*50)
        print("💜 AISHA — Interactive Test Mode")
        print("Type 'quit' to exit")
        print("="*50 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ["quit", "exit", "bye", "q"]:
                    print("Aisha: Goodbye Ajay! 💜 Miss you already!")
                    break
                if user_input:
                    response = aisha.think(user_input)
                    print(f"\nAisha: {response}\n")
            except KeyboardInterrupt:
                print("\nAisha: Bye Ajay! 💜")
                break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🌟 AISHA — System Check")
    print("=" * 50)
    
    env_ok = test_env_vars()
    
    if not env_ok:
        print("\n❌ Fix your .env file first, then run again.")
        sys.exit(1)
    
    gemini_ok = test_gemini()
    supabase_ok = test_supabase()
    
    if gemini_ok:
        if "--interactive" in sys.argv or "-i" in sys.argv:
            interactive_mode()
        else:
            run_chat_test()
            print("\n💡 Tip: Run with -i flag for interactive chat:")
            print("   python scripts/test_aisha.py -i")
    else:
        print("\n❌ Fix Gemini API key first, then run again.")
