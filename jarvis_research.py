from duckduckgo_search import DDGS
import json

def search(query):
    print(f"\n--- Searching: {query} ---")
    try:
        results = DDGS().text(query, max_results=5)
        for i, r in enumerate(results):
            print(f"{i+1}. {r['title']}")
            print(f"   {r['body'][:200]}...")
            print(f"   {r['href']}")
    except Exception as e:
        print(f"Search failed: {e}")

search("open source jarvis ai architecture github")
search("enterprise multi agent ai architecture patterns")
search("LLM memory graph database vector hybrid memgpt")
search("autonomous ai code execution sandbox architecture")
