#!/usr/bin/env python3
# bridge/quant_bridge.py
import argparse
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quant.api import QuantAPI


def main():
    parser = argparse.ArgumentParser(description="Quantitative analysis bridge")
    parser.add_argument("--persona", default="zettaranc", help="Persona name")
    parser.add_argument("--task", required=True, choices=["analyze", "backtest", "indicators"])
    parser.add_argument("--code", required=True, help="Stock code")
    parser.add_argument("--start", help="Start date (YYYYMMDD)")
    parser.add_argument("--end", help="End date (YYYYMMDD)")
    parser.add_argument("--indicators", nargs="+", help="Indicators to calculate")
    args = parser.parse_args()

    api = QuantAPI(persona_name=args.persona)

    if args.task == "analyze":
        result = api.analyze_stock(args.code, indicators=args.indicators)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.task == "backtest":
        if not args.start or not args.end:
            print("Error: --start and --end required for backtest")
            sys.exit(1)
        result = api.backtest(args.code, args.start, args.end)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.task == "indicators":
        result = api.get_available_indicators()
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
