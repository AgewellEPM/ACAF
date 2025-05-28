# knowledge_base_manager.py
# Manages the Worker Mind's local knowledge base (AAC packs).
# This module allows loading, querying, and updating structured knowledge.

import json
import os
from typing import Dict, Any, List

class KnowledgeBaseManager:
    def __init__(self, kb_file='aac_theory_pack.json'):
        self.kb_file = kb_file
        self.knowledge_base: Dict[str, Any] = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Loads the knowledge base from a JSON file."""
        if os.path.exists(self.kb_file):
            try:
                with open(self.kb_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {self.kb_file}: {e}. Initializing empty KB.")
                return {"pack_name": "Default KB", "version": "0.0", "concepts": [], "rules": []}
            except Exception as e:
                print(f"Error loading KB from {self.kb_file}: {e}. Initializing empty KB.")
                return {"pack_name": "Default KB", "version": "0.0", "concepts": [], "rules": []}
        return {"pack_name": "Default KB", "version": "0.0", "concepts": [], "rules": []}

    def _save_knowledge_base(self):
        """Saves the current knowledge base to the JSON file."""
        try:
            with open(self.kb_file, 'w') as f:
                json.dump(self.knowledge_base, f, indent=4)
        except Exception as e:
            print(f"Error saving KB to {self.kb_file}: {e}")

    def load_aac_pack(self, aac_data: Dict[str, Any]):
        """
        Loads or updates the knowledge base with data from an AAC pack.
        This overwrites the current KB with the new pack's content.
        In a more advanced system, this would merge or version control.
        """
        print(f"Loading AAC pack: {aac_data.get('pack_name', 'Unnamed Pack')}")
        self.knowledge_base = aac_data
        self._save_knowledge_base()
        print("AAC pack loaded successfully.")

    def query_knowledge_base(self, query: str) -> str:
        """
        Queries the knowledge base for relevant information.
        This is a simple keyword-based search for demonstration.
        In a real system, this would involve semantic search or graph traversal.
        """
        query_lower = query.lower()
        results = []

        # Search concepts
        for concept in self.knowledge_base.get("concepts", []):
            if query_lower in concept.get("name", "").lower() or \
               query_lower in concept.get("description", "").lower():
                results.append(f"Concept: {concept.get('name')} - {concept.get('description')}")

        # Search rules
        for rule in self.knowledge_base.get("rules", []):
            if query_lower in rule.get("rule", "").lower():
                results.append(f"Rule: {rule.get('rule')}")

        if results:
            return "Found in KB:\n" + "\n".join(results)
        else:
            return f"No direct information found in KB for '{query}'."

    def add_concept(self, concept_id: str, name: str, description: str):
        """Adds a new concept to the knowledge base."""
        concepts = self.knowledge_base.get("concepts", [])
        concepts.append({"id": concept_id, "name": name, "description": description})
        self.knowledge_base["concepts"] = concepts
        self._save_knowledge_base()
        print(f"Concept '{name}' added to KB.")

    def add_rule(self, rule_id: str, concept_ids: List[str], rule_text: str):
        """Adds a new rule to the knowledge base, linking to concepts."""
        rules = self.knowledge_base.get("rules", [])
        rules.append({"id": rule_id, "concept_ids": concept_ids, "rule": rule_text})
        self.knowledge_base["rules"] = rules
        self._save_knowledge_base()
        print(f"Rule '{rule_text}' added to KB.")

    def get_knowledge_base_content(self) -> Dict[str, Any]:
        """Returns the entire content of the knowledge base."""
        return self.knowledge_base

