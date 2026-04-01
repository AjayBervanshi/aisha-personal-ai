"""
Quick live key tester — runs all providers and prints status.
Usage: PYTHONUTF8=1 python tests/test_keys_live.py
"""
import os, sys, time, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

PASS = "[PASS]"
FAIL = "[FAIL]"
results = {}

def _test(name, fn):
    t = time.time()
    try:
        code, msg = fn()
        elapsed = round(time.time() - t, 2)
        ok = code == 200
        results[name] = (ok, code, msg, elapsed)
        print(f"  {'[OK] ' if ok else '[XX]'} {name:<35} HTTP {code}  {elapsed}s  {msg[:60]}")
    except Exception as e:
        elapsed = round(time.time() - t, 2)
        results[name] = (False, 0, str(e), elapsed)
        print(f"  [XX] {name:<35} ERR  {elapsed}s  {str(e)[:60]}")

gemini_key = os.getenv("GEMINI_API_KEY", "")

# Gemini models
for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite",
              "gemini-1.5-flash", "gemini-1.5-flash-8b"]:
    def _g(m=model):
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}",
            json={"contents": [{"parts": [{"text": "Say OK in one word"}]}]},
            timeout=15
        )
        text = ""
        if r.status_code == 200:
            try: text = r.json()["candidates"][0]["content"]["parts"][0]["text"][:30]
            except Exception: text = "parsed error"
        else:
            text = r.text[:80]
        return r.status_code, text
    _test(f"gemini/{model}", _g)

# Groq
def test_groq():
    key = os.getenv("GROQ_API_KEY", "")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5},
        timeout=15
    )
    return r.status_code, r.text[:80]
_test("groq/llama-3.3-70b", test_groq)

# Groq free models
for gmodel in ["llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]:
    def _gq(m=gmodel):
        key = os.getenv("GROQ_API_KEY", "")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": m, "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5},
            timeout=15
        )
        return r.status_code, r.text[:60]
    _test(f"groq/{gmodel}", _gq)

# OpenAI
def test_openai():
    key = os.getenv("OPENAI_API_KEY", "")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini", "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5},
        timeout=15
    )
    return r.status_code, r.text[:80]
_test("openai/gpt-4o-mini", test_openai)

# Anthropic
def test_anthropic():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version":"2023-06-01", "Content-Type":"application/json"},
        json={"model":"claude-haiku-4-5-20251001","max_tokens":5,"messages":[{"role":"user","content":"Say OK"}]},
        timeout=15
    )
    return r.status_code, r.text[:80]
_test("anthropic/claude-haiku", test_anthropic)

# xAI - grok-3-mini (model from .env)
def test_xai_mini():
    key = os.getenv("XAI_API_KEY", "")
    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "grok-3-mini", "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5},
        timeout=15
    )
    return r.status_code, r.text[:80]
_test("xai/grok-3-mini", test_xai_mini)

# xAI - grok-2-latest
def test_xai_grok2():
    key = os.getenv("XAI_API_KEY", "")
    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "grok-2-latest", "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5},
        timeout=15
    )
    return r.status_code, r.text[:80]
_test("xai/grok-2-latest", test_xai_grok2)

# HuggingFace
def test_hf():
    key = os.getenv("HUGGINGFACE_API_KEY", "")
    r = requests.post(
        "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
        headers={"Authorization": f"Bearer {key}"},
        json={"inputs": "Say OK", "parameters": {"max_new_tokens": 5}},
        timeout=20
    )
    return r.status_code, r.text[:80]
_test("huggingface/zephyr-7b", test_hf)

# NVIDIA NIM
def test_nvidia():
    key = os.getenv("NVIDIA_KEY_01", "")
    r = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model":"meta/llama-3.3-70b-instruct","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5},
        timeout=25
    )
    return r.status_code, r.text[:60]
_test("nvidia/llama-3.3-70b", test_nvidia)

print("\n=== SUMMARY ===")
working = [k for k,v in results.items() if v[0]]
dead    = [k for k,v in results.items() if not v[0]]
print(f"Working ({len(working)}): {', '.join(working)}")
print(f"Dead    ({len(dead)}): {', '.join(dead)}")
