#!/usr/bin/env python3
"""Knowledge base sync with batch progress and resume support."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from knowledge.chunker import MarkdownChunker
from knowledge.embeddings import TongyiEmbedding
from knowledge.store import KnowledgeStore
from shared.config import get_knowledge_base_config

_STATE_FILE = Path(__file__).parent.parent / "knowledge" / ".sync_state.json"


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def collect_md_files(vault_path: Path, include: list, exclude: list) -> list[Path]:
    files = []
    for pattern in include:
        files.extend(vault_path.rglob(pattern))
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


def sync_knowledge_base(kb_name: str):
    cfg = get_knowledge_base_config(kb_name)
    vault_path = Path(cfg["vault_path"])
    collection = cfg["collection"]
    chunker_cfg = cfg.get("chunker", {})
    sync_cfg = cfg.get("sync", {})

    if not vault_path.exists():
        raise FileNotFoundError(f"Vault path not found: {vault_path}")

    chunker = MarkdownChunker(
        max_size=chunker_cfg.get("max_chunk_size", 1000),
        preserve_hierarchy=chunker_cfg.get("preserve_hierarchy", True),
    )
    store = KnowledgeStore()
    embedder = TongyiEmbedding()

    # Load state
    state = {}
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass

    # Collect files
    include = sync_cfg.get("include_patterns", ["*.md"])
    exclude = sync_cfg.get("exclude_patterns", [".obsidian/**", "assets/**"])
    files = collect_md_files(vault_path, include, exclude)
    print(f"[1/5] Found {len(files)} files to process")

    # Track changes
    kb_state = state.get(kb_name, {})
    changed_files = []

    for file in files:
        rel_path = str(file.relative_to(vault_path))
        current_hash = file_hash(file)
        if kb_state.get(rel_path) != current_hash:
            changed_files.append((file, rel_path))
            kb_state[rel_path] = current_hash

    # Remove deleted files
    current_paths = {str(f.relative_to(vault_path)) for f in files}
    for d in set(kb_state.keys()) - current_paths:
        del kb_state[d]

    if not changed_files:
        print(f"Knowledge base '{kb_name}' is up to date.")
        return 0

    print(f"[2/5] Processing {len(changed_files)} changed files...")

    # Process changed files
    all_chunks = []
    for i, (file, rel_path) in enumerate(changed_files):
        chunks = chunker.split_file(file)
        for chunk in chunks:
            chunk.source_file = rel_path
        all_chunks.extend(chunks)
        if (i + 1) % 50 == 0:
            print(f"  Chunked {i + 1}/{len(changed_files)} files, {len(all_chunks)} chunks so far")

    if not all_chunks:
        print("No chunks to sync.")
        return 0

    print(f"[3/5] Total chunks: {len(all_chunks)}")

    # Delete old collection
    print("[4/5] Clearing old collection...")
    store.delete_collection(collection)

    # Add in batches with progress
    batch_size = 100  # ChromaDB add batch size
    total_batches = (len(all_chunks) + batch_size - 1) // batch_size
    print(f"[5/5] Embedding and adding {len(all_chunks)} chunks in {total_batches} batches...")

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(all_chunks))
        batch = all_chunks[start:end]

        ids = [f"{kb_name}_{start + i}" for i in range(len(batch))]
        texts = [c.content for c in batch]
        metadatas = [
            {
                "source_file": c.source_file,
                "heading_path": c.heading_path,
                "start_line": c.start_line,
                "end_line": c.end_line,
            }
            for c in batch
        ]

        print(f"  Batch {batch_idx + 1}/{total_batches}: embedding {len(batch)} chunks...", end=" ", flush=True)
        t0 = time.time()
        embeddings = embedder.embed(texts)
        t1 = time.time()

        col = store.get_or_create_collection(collection)
        col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        t2 = time.time()

        print(f"embed={t1-t0:.1f}s, store={t2-t1:.1f}s, total={t2-t0:.1f}s")

    # Save state
    state[kb_name] = kb_state
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Synced {len(changed_files)} files, {len(all_chunks)} chunks to '{kb_name}'")
    return len(all_chunks)


if __name__ == "__main__":
    kb = sys.argv[1] if len(sys.argv) > 1 else "zettaranc"
    count = sync_knowledge_base(kb)
    print(f"Total: {count} chunks")
