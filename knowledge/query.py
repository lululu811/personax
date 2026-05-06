from typing import List, Dict, Any

from knowledge.store import KnowledgeStore
from shared.config import get_persona_config


def query_knowledge(question: str, persona_name: str, n_results: int = 5) -> Dict[str, Any]:
    """
    Query knowledge bases for a given persona.
    Returns merged results from all allowed knowledge bases.
    """
    config = get_persona_config(persona_name)
    allowed_kb = config["knowledge_bases"]

    store = KnowledgeStore()
    all_results = {}

    for kb_name in allowed_kb:
        try:
            results = store.query(kb_name, question, n_results=n_results)
            all_results[kb_name] = results
        except Exception as e:
            all_results[kb_name] = {"error": str(e)}

    return all_results


def format_results(results: Dict[str, Any]) -> str:
    """Format query results into a context string for LLM."""
    lines = []
    for kb_name, kb_results in results.items():
        if "error" in kb_results:
            continue

        documents = kb_results.get("documents", [[]])[0]
        metadatas = kb_results.get("metadatas", [[]])[0]
        distances = kb_results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            source = meta.get("source_file", "unknown")
            heading = meta.get("heading_path", "")
            lines.append(f"[{source} > {heading}] (relevance: {1 - dist:.2f})")
            lines.append(doc[:500])  # Truncate long docs
            lines.append("---")

    return "\n".join(lines)
