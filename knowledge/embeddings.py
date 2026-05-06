import os
import time
from typing import List

import requests


class TongyiEmbedding:
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-v3"):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings = []
        batch_size = 25

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {
                "model": self.model,
                "input": {
                    "texts": batch,
                },
            }

            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            embeddings = data["output"]["embeddings"]
            all_embeddings.extend([e["embedding"] for e in embeddings])

            time.sleep(0.1)  # Rate limit protection

        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        results = self.embed([text])
        return results[0] if results else []
