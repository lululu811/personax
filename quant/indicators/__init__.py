"""Quant indicators package.

Legacy indicator package. Most indicators have been migrated to:
    tools/quant/technical/

Only MA remains here as it does not exist in the new architecture.
"""

from quant.indicators.ma import calculate_ma

__all__ = ["calculate_ma"]
