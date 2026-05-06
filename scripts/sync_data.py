#!/usr/bin/env python3
# scripts/sync_data.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.sync import SyncEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--persona", default="zettaranc", help="Persona name")
    args = parser.parse_args()

    engine = SyncEngine(persona_name=args.persona)
    try:
        result = engine.sync_stock(args.code)
        print(f"Sync result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
