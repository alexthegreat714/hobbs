"""
Pattern utilities for Hobbs Agent learning.

Provides statistical helpers for pattern detection,
rolling averages, correlation analysis, and anomaly scoring.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def rolling_avg(values: List[float], window: int) -> List[float]:
    """
    Compute rolling average over a window.

    Args:
        values: List of numeric values
        window: Window size for averaging

    Returns:
        List of rolling averages (shorter than input by window-1)
    """
    if not values or window <= 0:
        return []

    if window > len(values):
        window = len(values)

    result = []
    for i in range(len(values) - window + 1):
        window_values = values[i:i + window]
        avg = sum(window_values) / len(window_values)
        result.append(avg)

    return result


def z_score(value: float, mean: float, std: float) -> float:
    """
    Calculate z-score (number of standard deviations from mean).

    Args:
        value: The value to score
        mean: Population mean
        std: Population standard deviation

    Returns:
        Z-score (0 if std is 0)
    """
    if std == 0:
        return 0.0
    return (value - mean) / std


def histogram(data: List[Any], bins: List[Any]) -> Dict[Any, int]:
    """
    Create a histogram by counting occurrences in bins.

    Args:
        data: List of values to bin
        bins: List of bin labels/values

    Returns:
        Dictionary mapping bin to count
    """
    result = {b: 0 for b in bins}
    for item in data:
        if item in result:
            result[item] += 1
    return result


def histogram_numeric(values: List[float], num_bins: int = 10) -> Dict[str, int]:
    """
    Create a numeric histogram with ranges.

    Args:
        values: List of numeric values
        num_bins: Number of bins to create

    Returns:
        Dictionary mapping range strings to counts
    """
    if not values:
        return {}

    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        return {f"{min_val:.2f}": len(values)}

    bin_width = (max_val - min_val) / num_bins
    result = {}

    for i in range(num_bins):
        low = min_val + i * bin_width
        high = min_val + (i + 1) * bin_width
        key = f"{low:.2f}-{high:.2f}"
        result[key] = 0

    for v in values:
        bin_idx = int((v - min_val) / bin_width)
        if bin_idx >= num_bins:
            bin_idx = num_bins - 1
        low = min_val + bin_idx * bin_width
        high = min_val + (bin_idx + 1) * bin_width
        key = f"{low:.2f}-{high:.2f}"
        result[key] = result.get(key, 0) + 1

    return result


def detect_peak_hours(hourly_counts: Dict[str, int], top_n: int = 3) -> List[str]:
    """
    Detect the top N peak hours from hourly counts.

    Args:
        hourly_counts: Dictionary mapping hour strings ("00"-"23") to counts
        top_n: Number of peak hours to return

    Returns:
        List of hour strings sorted by count descending
    """
    if not hourly_counts:
        return []

    sorted_hours = sorted(
        hourly_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return [h for h, c in sorted_hours[:top_n] if c > 0]


def correlation(xs: List[float], ys: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient.

    Args:
        xs: First list of values
        ys: Second list of values (must be same length)

    Returns:
        Correlation coefficient (-1 to 1), or 0 if invalid
    """
    if not xs or not ys or len(xs) != len(ys):
        return 0.0

    n = len(xs)
    if n < 2:
        return 0.0

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    # Calculate covariance and standard deviations
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
    std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / n)
    std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / n)

    if std_x == 0 or std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


def mean(values: List[float]) -> float:
    """Calculate mean of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def std_dev(values: List[float]) -> float:
    """Calculate standard deviation of values."""
    if len(values) < 2:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def detect_trend(values: List[float]) -> str:
    """
    Detect simple trend direction.

    Args:
        values: Time-series values

    Returns:
        "increasing", "decreasing", or "stable"
    """
    if len(values) < 3:
        return "stable"

    # Simple linear regression slope
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = mean(values)

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Normalize slope by value range
    value_range = max(values) - min(values) if max(values) != min(values) else 1
    normalized_slope = slope / value_range * n

    if normalized_slope > 0.1:
        return "increasing"
    elif normalized_slope < -0.1:
        return "decreasing"
    return "stable"


def compute_statistics(values: List[float]) -> Dict[str, float]:
    """
    Compute comprehensive statistics for a list of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with avg, std_dev, min, max, count
    """
    if not values:
        return {
            "avg": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0,
        }

    return {
        "avg": mean(values),
        "std_dev": std_dev(values),
        "min": min(values),
        "max": max(values),
        "count": len(values),
    }
