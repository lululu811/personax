#!/usr/bin/env python3
# scripts/setup.py
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.db import Database
from knowledge.store import KnowledgeStore


def check_env():
    required = ["DASHSCOPE_API_KEY", "TUSHARE_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"Missing environment variables: {missing}")
        print("Please set them in .env file and run: source .env")
        return False
    return True


def init_data_layer():
    print("Initializing data layer...")
    db = Database()
    tables = db.conn.execute("SHOW TABLES").fetchall()
    print(f"Created tables: {[t[0] for t in tables]}")
    db.close()
    print("Data layer initialized.")


def init_knowledge_layer():
    print("Initializing knowledge layer...")
    store = KnowledgeStore()
    collections = store.list_collections()
    print(f"Existing collections: {collections}")
    print("Knowledge layer initialized.")


def main():
    if not check_env():
        sys.exit(1)

    init_data_layer()
    init_knowledge_layer()
    print("\nSetup complete!")


if __name__ == "__main__":
    main()
