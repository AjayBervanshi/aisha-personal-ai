"""
Test all 22 NVIDIA NIM keys and report which are alive.
Usage: PYTHONUTF8=1 python tests/test_nvidia_keys.py
"""
import os, sys, time, requests, concurrent.futures
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

NVIDIA_KEYS = {
    "KEY_01": "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",
    "KEY_02": "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",
    "KEY_03": "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",
    "KEY_04": "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",
    "KEY_05": "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",
    "KEY_06": "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",
    "KEY_07": "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",
    "KEY_08": "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",
    "KEY_09": "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",
    "KEY_10": "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",
    "KEY_11": "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",
    "KEY_12": "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",
    "KEY_13": "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",
    "KEY_14": "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",
    "KEY_15": "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",
    "KEY_16": "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",
    "KEY_17": "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",
    "KEY_18": "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",
    "KEY_19": "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",
    "KEY_20": "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",
    "KEY_21": "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",
    "KEY_22": "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",
}

def test_key(name, key):
    t = time.time()
    try:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 5
            },
            timeout=20
        )
        elapsed = round(time.time() - t, 2)
        if r.status_code == 200:
            return name, True, r.status_code, elapsed, "OK"
        else:
            snippet = r.text[:60].replace('\n', ' ')
            return name, False, r.status_code, elapsed, snippet
    except Exception as e:
        elapsed = round(time.time() - t, 2)
        return name, False, 0, elapsed, str(e)[:60]

print("Testing all 22 NVIDIA keys in parallel...\n")
results = {}

with concurrent.futures.ThreadPoolExecutor(max_workers=11) as pool:
    futures = {pool.submit(test_key, n, k): n for n, k in NVIDIA_KEYS.items()}
    for future in concurrent.futures.as_completed(futures):
        name, ok, code, elapsed, msg = future.result()
        results[name] = (ok, code, elapsed, msg)

# Sort by key number for clean output
working = []
dead = []
for name in sorted(results.keys()):
    ok, code, elapsed, msg = results[name]
    status = "[OK] " if ok else "[XX]"
    print(f"  {status} {name}  HTTP {code}  {elapsed}s  {msg}")
    if ok:
        working.append(name)
    else:
        dead.append(f"{name}(HTTP{code})")

print(f"\n=== NVIDIA KEY AUDIT ===")
print(f"Working: {len(working)}/22  -> {', '.join(working)}")
print(f"Dead:    {len(dead)}/22  -> {', '.join(dead)}")
print(f"\nEstimated free credits/month: {len(working)} x 1,000 = {len(working)*1000:,}")
