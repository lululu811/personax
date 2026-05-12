# orchestration/review/cli.py
"""CLI for signal review system.

Usage:
    python -m orchestration.review.cli weekly
    python -m orchestration.review.cli monthly
"""
import argparse
import sys
from orchestration.review.review_service import ReviewService


def main():
    parser = argparse.ArgumentParser(description="Signal Review CLI")
    parser.add_argument(
        "period",
        choices=["weekly", "monthly"],
        help="Review period"
    )
    parser.add_argument(
        "--db-path",
        default="~/.personax/review.db",
        help="Database path"
    )
    args = parser.parse_args()

    service = ReviewService(db_path=args.db_path)

    if args.period == "weekly":
        result = service.review_weekly()
    else:
        result = service.review_monthly()

    print(result.report)
    print()
    print("Weight Adjustments:")
    for source, adjustment in result.weight_adjustments.items():
        sign = "+" if adjustment > 0 else ""
        print(f"  {source}: {sign}{adjustment}")

    return 0


if __name__ == "__main__":
    sys.exit(main())