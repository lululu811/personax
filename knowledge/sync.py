import hashlib
import json
from pathlib import Path
from typing import List

from knowledge.chunker import MarkdownChunker
from knowledge.store import KnowledgeStore
from shared.config import get_knowledge_base_config

_STATE_FILE = Path(__file__).parent / ".sync_state.json"


class KnowledgeSyncEngine:
    def __init__(self):
        self.store = KnowledgeStore()
        self.chunker = MarkdownChunker()
        self._load_state()

    def _load_state(self):
        if _STATE_FILE.exists():
            try:
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except (json.JSONDecodeError, ValueError):
                self.state = {}
        else:
            self.state = {}

    def _save_state(self):
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _collect_md_files(self, vault_path: Path, include: List[str], exclude: List[str]) -> List[Path]:
        files = []
        for pattern in include:
            files.extend(vault_path.rglob(pattern))

        # Apply exclusions
        filtered = []
        for f in files:
            rel = f.relative_to(vault_path)
            excluded = False
            for ex in exclude:
                if rel.match(ex):
                    excluded = True
                    break
            if not excluded:
                filtered.append(f)

        return sorted(filtered)

    def sync_knowledge_base(self, kb_name: str):
        cfg = get_knowledge_base_config(kb_name)
        vault_path = Path(cfg["vault_path"])
        collection = cfg["collection"]
        chunker_cfg = cfg.get("chunker", {})
        sync_cfg = cfg.get("sync", {})

        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path not found: {vault_path}")

        # Update chunker config
        self.chunker.max_size = chunker_cfg.get("max_chunk_size", 1000)
        self.chunker.preserve_hierarchy = chunker_cfg.get("preserve_hierarchy", True)

        # Collect files
        include = sync_cfg.get("include_patterns", ["*.md"])
        exclude = sync_cfg.get("exclude_patterns", [".obsidian/**", "assets/**"])
        files = self._collect_md_files(vault_path, include, exclude)

        # Track changes
        kb_state = self.state.get(kb_name, {})
        changed_files = []

        for file in files:
            rel_path = str(file.relative_to(vault_path))
            current_hash = self._file_hash(file)

            if kb_state.get(rel_path) != current_hash:
                changed_files.append((file, rel_path))
                kb_state[rel_path] = current_hash

        # Remove deleted files from state
        current_paths = {str(f.relative_to(vault_path)) for f in files}
        deleted = set(kb_state.keys()) - current_paths
        for d in deleted:
            del kb_state[d]

        if not changed_files:
            print(f"Knowledge base '{kb_name}' is up to date.")
            return 0

        # Process changed files
        all_chunks = []
        for file, rel_path in changed_files:
            chunks = self.chunker.split_file(file)
            for chunk in chunks:
                chunk.source_file = rel_path
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # Delete old collection and re-add
        self.store.delete_collection(collection)
        ids = [f"{kb_name}_{i}" for i in range(len(all_chunks))]
        self.store.add_documents(collection, all_chunks, ids=ids)

        # Save state
        self.state[kb_name] = kb_state
        self._save_state()

        print(f"Synced {len(changed_files)} files, {len(all_chunks)} chunks to '{kb_name}'")
        return len(all_chunks)
