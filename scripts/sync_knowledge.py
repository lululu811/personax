#!/usr/bin/env python3
# scripts/sync_knowledge.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from knowledge.sync import KnowledgeSyncEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb", required=True, help="Knowledge base name")
    args = parser.parse_args()

    engine = KnowledgeSyncEngine()
    try:
        count = engine.sync_knowledge_base(args.kb)
        print(f"Synced {count} chunks")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
