"""
riya.py — Research Agent
========================
Riya is the first agent in the pipeline.
Given a topic, she:
1. Researches facts using DuckDuckGo (free, no API key)
2. Finds trending angles
3. Identifies target audience
4. Extracts keywords for SEO
5. Saves all findings to Supabase for Lexi (script writer)
"""

import os
import json
import requests
from typing import Any
from src.agents.base_agent import BaseAgent


class RiyaAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Riya",
            role="Senior Content Researcher for YouTube",
            personality="""You are Riya, an expert YouTube content researcher.
You research topics deeply and provide structured, factual, and engaging research summaries.
Your output always includes: key facts, target audience insights, hook ideas, and SEO keywords.
You are thorough, accurate, and always think about what will make viewers click and watch.
Format your research clearly with numbered sections."""
        )

    def run_task(self, job_id: str, topic: str) -> dict:
        """Research a topic and return structured findings."""
        self._update_job_status(job_id, "researching")

        # Step 1: Web search via DuckDuckGo (free, no API key needed)
        search_results = self._ddg_search(topic)

        # Step 2: AI-powered research synthesis
        research = self._synthesize_research(topic, search_results)

        # Step 3: Extract keywords for SEO
        keywords = self._extract_keywords(topic, research)

        output = {
            "topic":    topic,
            "findings": research,
            "keywords": keywords,
            "sources":  search_results[:3]  # Top 3 sources
        }

        # Save to Supabase
        self._save_output(job_id, "yt_research", {
            "topic":    topic,
            "findings": research,
            "keywords": keywords,
            "sources":  [s.get("url", "") for s in search_results[:5]]
        })

        self.log.info(f"[Riya] Research complete: {len(research.split())} words")
        return output

    def _ddg_search(self, topic: str) -> list:
        """
        Search DuckDuckGo for research — completely free, no API key.
        Returns list of {"title": ..., "url": ..., "snippet": ...}
        """
        try:
            # DuckDuckGo Instant Answer API (free, no key needed)
            params = {
                "q": topic,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            r = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=10,
                headers={"User-Agent": "Aisha-Research-Bot/1.0"}
            )
            data = r.json()

            results = []
            # Abstract (main summary)
            if data.get("AbstractText"):
                results.append({
                    "title":   data.get("Heading", topic),
                    "url":     data.get("AbstractURL", ""),
                    "snippet": data["AbstractText"]
                })
            # Related topics
            for item in data.get("RelatedTopics", [])[:4]:
                if isinstance(item, dict) and item.get("Text"):
                    results.append({
                        "title":   item.get("Text", "")[:60],
                        "url":     item.get("FirstURL", ""),
                        "snippet": item.get("Text", "")
                    })
            return results

        except Exception as e:
            self.log.warning(f"[Riya] DuckDuckGo search failed: {e}")
            return []

    def _synthesize_research(self, topic: str, search_results: list) -> str:
        """Use Ollama to synthesize research from search results."""
        search_text = "\n".join([
            f"- {r['snippet']}" for r in search_results if r.get("snippet")
        ]) or "No external search results available."

        prompt = f"""Research topic for YouTube video: "{topic}"

Search results found:
{search_text[:2000]}

As a professional YouTube researcher, provide a comprehensive research brief with:

1. HOOK IDEAS (3 attention-grabbing opening lines)
2. KEY FACTS (7-10 specific, interesting facts viewers want to know)
3. TARGET AUDIENCE (who will watch this, their pain points)
4. BEST VIDEO ANGLE (the most unique/engaging approach)
5. COMPETITOR GAPS (what other videos miss that we should cover)
6. RECOMMENDED LENGTH (in minutes, with justification)
7. CONTENT WARNINGS (anything sensitive to handle carefully)

Write detailed, specific content — not generic advice."""

        return self.think(prompt)

    def _extract_keywords(self, topic: str, research: str) -> list:
        """Extract SEO keywords from research."""
        result = self.think_structured(
            f"""Extract the 15 most important SEO keywords for a YouTube video about: "{topic}"
            
Context from research: {research[:500]}

Return JSON: {{"keywords": ["keyword1", "keyword2", ...]}}
Focus on: high search volume, low competition, relevant to Indian audience."""
        )
        return result.get("keywords", [topic])
