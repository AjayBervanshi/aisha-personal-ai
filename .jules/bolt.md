## 2026-04-02 - Batch database updates in memory deduplication
**Learning:** Found an N+1 query loop in `MemoryCompressor.deduplicate_memories` where each `is_active=False` update for duplicate memory was done using `.eq('id', archive_id).execute()`. For 100 duplicates, this makes 100 network roundtrips.
**Action:** Collected all `archive_id`s in a list and batched them in chunks of 100. Used `.in_('id', batch_ids).execute()` instead, reducing the 100 network requests down to just 1 request per chunk.
