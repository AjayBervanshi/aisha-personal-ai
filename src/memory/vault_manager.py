import json
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
import os

log = logging.getLogger(__name__)

class VaultManager:
    """
    JARVIS Feature 1.3: Knowledge Graph Vault.
    Manages Entities, Facts, and Relationships.
    """
    def __init__(self, supabase_client: Optional[Client] = None):
        if supabase_client:
            self.supabase = supabase_client
        else:
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))
            try:
                self.supabase = create_client(url, key)
            except Exception as e:
                log.error(f"Failed to init Supabase in Vault: {e}")
                self.supabase = None

    def _get_or_create_entity(self, name: str, entity_type: str, description: str = "") -> Optional[str]:
        if not self.supabase: return None
        try:
            # Check if exists
            name_lower = name.strip().lower()
            res = self.supabase.table("vault_entities").select("id").eq("name", name_lower).eq("type", entity_type).execute()
            if res.data:
                return res.data[0]["id"]

            # Create new
            new_res = self.supabase.table("vault_entities").insert({
                "name": name_lower,
                "type": entity_type,
                "description": description
            }).execute()

            if new_res.data:
                return new_res.data[0]["id"]
        except Exception as e:
            log.error(f"Vault error creating entity {name}: {e}")
        return None

    def add_fact(self, entity_name: str, entity_type: str, fact: str) -> bool:
        """Add a discrete fact to an entity."""
        if not self.supabase: return False
        entity_id = self._get_or_create_entity(entity_name, entity_type)
        if not entity_id: return False

        try:
            self.supabase.table("vault_facts").insert({
                "entity_id": entity_id,
                "fact": fact
            }).execute()
            log.info(f"[Vault] Added fact for {entity_name}: {fact}")
            return True
        except Exception as e:
            log.error(f"Vault error adding fact: {e}")
            return False

    def add_relationship(self, source_name: str, source_type: str, target_name: str, target_type: str, rel_type: str) -> bool:
        """Create a relationship edge between two entities."""
        if not self.supabase: return False
        source_id = self._get_or_create_entity(source_name, source_type)
        target_id = self._get_or_create_entity(target_name, target_type)

        if not source_id or not target_id: return False

        try:
            self.supabase.table("vault_relationships").upsert({
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "relationship_type": rel_type
            }, on_conflict="source_entity_id, target_entity_id, relationship_type").execute()
            log.info(f"[Vault] Added relationship: {source_name} --[{rel_type}]--> {target_name}")
            return True
        except Exception as e:
            log.error(f"Vault error adding relationship: {e}")
            return False

    def retrieve_entity_graph(self, entity_name: str) -> str:
        """Retrieves all facts and relationships for a given entity."""
        if not self.supabase: return ""
        name_lower = entity_name.strip().lower()

        try:
            # Get entity
            ent_res = self.supabase.table("vault_entities").select("id, type, description").eq("name", name_lower).execute()
            if not ent_res.data:
                return ""

            e_id = ent_res.data[0]["id"]
            e_type = ent_res.data[0]["type"]

            # Get facts
            facts_res = self.supabase.table("vault_facts").select("fact").eq("entity_id", e_id).execute()
            facts = [f["fact"] for f in facts_res.data]

            # Formulate text
            lines = [f"Entity: {entity_name} ({e_type})"]
            if facts:
                lines.append("Facts:")
                for fact in facts:
                    lines.append(f" - {fact}")

            return "\n".join(lines)

        except Exception as e:
            log.error(f"Vault retrieval error: {e}")
            return ""

# Global singleton
vault = VaultManager()
