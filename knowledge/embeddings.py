import os
import time
from typing import List

import requests


class TongyiEmbedding:
    def __init__(self, api_key: str | None = None, model: str = "text-embedding-v4"):
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
        batch_size = 10

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {
                "model": self.model,
                "input": {
                    "texts": batch,
                },
            }

            # Retry with exponential backoff
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        self.base_url, headers=headers, json=payload, timeout=60
                    )
                    response.raise_for_status()
                    break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if attempt == max_retries - 1:
                        raise
                    wait = 2 ** attempt + 0.5
                    print(f"  SSL/Connection error, retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 429:
                        wait = 2 ** attempt + 1
                        print(f"  Rate limited, retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise

            data = response.json()
            embeddings = data["output"]["embeddings"]
            all_embeddings.extend([e["embedding"] for e in embeddings])

            time.sleep(0.15)  # Rate limit protection

        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        results = self.embed([text])
        return results[0] if results else []
