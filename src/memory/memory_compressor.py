"""
memory_compressor.py
====================
Long-term memory hygiene for Aisha.

Over time, aisha_memory accumulates duplicate or stale facts.
This module handles:
  - Deduplication via cosine similarity of embeddings
  - Importance decay for old memories not recalled recently
  - Importance promotion when a memory is frequently recalled
  - Weekly cleanup (run Sunday 3 AM via autonomous_loop)

Usage:
    compressor = MemoryCompressor(memory_manager)
    compressor.run_weekly_cleanup()
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.core.logger import get_logger

log = get_logger("MemoryCompressor")

# Memories older than this many days get importance decayed
DECAY_AFTER_DAYS = 60

# Cosine similarity threshold above which two memories are considered duplicates
DUPLICATE_THRESHOLD = 0.92

# Minimum importance to keep a memory (memories decayed below this are archived)
MIN_IMPORTANCE = 1


class MemoryCompressor:
    """
    Performs memory hygiene on the aisha_memory table.
    """

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.db = memory_manager.db

    # ── Public ─────────────────────────────────────────────────────────────

    def run_weekly_cleanup(self) -> Dict[str, int]:
        """
        Full cleanup pipeline. Returns stats dict.
        Called by autonomous_loop every Sunday at 3 AM.
        """
        log.info("event=weekly_cleanup_start")
        stats = {
            "duplicates_removed": 0,
            "memories_decayed": 0,
            "errors": 0,
        }
        try:
            stats["duplicates_removed"] = self.deduplicate_memories()
        except Exception as e:
            log.error("event=dedup_failed — %s", str(e))
            stats["errors"] += 1
        try:
            stats["memories_decayed"] = self.decay_old_memories()
        except Exception as e:
            log.error("event=decay_failed — %s", str(e))
            stats["errors"] += 1
        log.info("event=weekly_cleanup_done", **stats)
        return stats

    def deduplicate_memories(self) -> int:
        """
        Find near-duplicate memories using embedding cosine similarity.
        Keeps the higher-importance one; archives the duplicate.
        Returns count of memories archived.
        """
        try:
            rows = (
                self.db.table("aisha_memory")
                .select("id, title, content, importance, embedding")
                .eq("is_active", True)
                .execute()
            ).data or []
        except Exception as e:
            log.error("event=dedup_fetch_failed — %s", str(e))
            return 0

        # Only process memories that have embeddings
        embedded = [r for r in rows if r.get("embedding")]
        archived_ids = set()
        archived_count = 0

        for i in range(len(embedded)):
            if embedded[i]["id"] in archived_ids:
                continue
            for j in range(i + 1, len(embedded)):
                if embedded[j]["id"] in archived_ids:
                    continue
                sim = self._cosine_similarity(embedded[i]["embedding"], embedded[j]["embedding"])
                if sim >= DUPLICATE_THRESHOLD:
                    # Keep higher importance; archive the other
                    if embedded[i].get("importance", 3) >= embedded[j].get("importance", 3):
                        archive_id = embedded[j]["id"]
                    else:
                        archive_id = embedded[i]["id"]
                    archived_ids.add(archive_id)
                    try:
                        self.db.table("aisha_memory").update({
                            "is_active": False,
                        }).eq("id", archive_id).execute()
                        archived_count += 1
                        log.info("event=duplicate_archived",
                                 title_a=embedded[i]["title"][:40],
                                 title_b=embedded[j]["title"][:40],
                                 similarity=round(sim, 3))
                    except Exception as e:
                        log.warning("event=archive_failed", memory_id=archive_id, error=str(e))

        return archived_count

    def decay_old_memories(self) -> int:
        """
        Reduce importance of memories that are old and haven't been recalled recently.
        Memories with importance 1 that are old get archived.
        Returns count of memories decayed.
        """
        cutoff = (datetime.now() - timedelta(days=DECAY_AFTER_DAYS)).isoformat()
        try:
            old_memories = (
                self.db.table("aisha_memory")
                .select("id, importance, title")
                .eq("is_active", True)
                .lt("updated_at", cutoff)
                .execute()
            ).data or []
        except Exception as e:
            log.error("event=decay_fetch_failed — %s", str(e))
            return 0

        decayed = 0
        for mem in old_memories:
            current_importance = mem.get("importance", 3)
            if current_importance <= MIN_IMPORTANCE:
                # Archive instead of decay further
                try:
                    self.db.table("aisha_memory").update({"is_active": False}).eq("id", mem["id"]).execute()
                    log.info("event=memory_archived", title=mem.get("title", "")[:40])
                    decayed += 1
                except Exception as e:
                    log.warning("event=archive_failed", error=str(e))
            else:
                # Decay by 1 step
                try:
                    self.db.table("aisha_memory").update({
                        "importance": current_importance - 1,
                    }).eq("id", mem["id"]).execute()
                    decayed += 1
                except Exception as e:
                    log.warning("event=decay_update_failed", error=str(e))

        return decayed

    def promote_importance(self, memory_id: str) -> bool:
        """
        Bump importance of a memory that was recalled (max 5).
        Called by MemoryManager when a semantic match is returned.
        """
        try:
            row = (
                self.db.table("aisha_memory")
                .select("importance")
                .eq("id", memory_id)
                .limit(1)
                .execute()
            ).data
            if not row:
                return False
            current = row[0].get("importance", 3)
            if current < 5:
                self.db.table("aisha_memory").update({
                    "importance": current + 1,
                    "updated_at": datetime.now().isoformat(),
                }).eq("id", memory_id).execute()
            return True
        except Exception as e:
            log.warning("event=promote_failed", memory_id=memory_id, error=str(e))
            return False

    # ── Internal ───────────────────────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
