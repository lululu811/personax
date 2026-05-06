#!/usr/bin/env python3
# bridge/knowledge_bridge.py
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from knowledge.query import query_knowledge, format_results


def main():
    parser = argparse.ArgumentParser(description="Query knowledge base for a persona")
    parser.add_argument("--persona", required=True, help="Persona name")
    parser.add_argument("question", nargs="+", help="Question to ask")
    parser.add_argument("--n-results", type=int, default=5, help="Number of results")
    args = parser.parse_args()

    question = " ".join(args.question)
    results = query_knowledge(question, args.persona, n_results=args.n_results)
    formatted = format_results(results)
    print(formatted)


if __name__ == "__main__":
    main()
