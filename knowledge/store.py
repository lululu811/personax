from pathlib import Path
from typing import List, Dict, Any

import chromadb

from knowledge.embeddings import TongyiEmbedding

_DB_ROOT = Path(__file__).parent / "vector_store"


class KnowledgeStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(_DB_ROOT)
        _DB_ROOT.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.embedder = TongyiEmbedding()

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, collection_name: str, chunks: List[Any], ids: List[str] | None = None):
        collection = self.get_or_create_collection(collection_name)

        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedder.embed(texts)

        if ids is None:
            ids = [f"{collection_name}_{i}" for i in range(len(chunks))]

        metadatas = [
            {
                "source_file": chunk.source_file,
                "heading_path": chunk.heading_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            }
            for chunk in chunks
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    def query(self, collection_name: str, question: str, n_results: int = 5) -> Dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        embedding = self.embedder.embed_single(question)

        return collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def delete_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]
