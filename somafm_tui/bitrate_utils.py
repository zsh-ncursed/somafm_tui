"""Bitrate utilities for SomaFM TUI.

Provides constants and functions for bitrate mapping and extraction.
Centralizes bitrate logic to avoid duplication across the codebase.
"""

import re
from typing import Dict, List, Optional, Tuple


# Standard bitrate labels in descending order
BITRATE_LABELS: List[str] = ["320k", "256k", "192k", "128k", "96k", "64k", "32k"]

# Mapping from bitrate number (from URL) to standard label
# SomaFM uses specific numbers: 320, 256, 192, 130 (for 128k), 96, 64, 32
BITRATE_NUM_TO_LABEL: Dict[int, str] = {
    320: "320k",
    256: "256k",
    192: "192k",
    130: "128k",  # SomaFM uses 130 for 128k
    128: "128k",
    96: "96k",
    64: "64k",
    32: "32k",
}

# Mapping from standard label back to URL number pattern
LABEL_TO_BITRATE_NUM: Dict[str, str] = {
    "320k": "320",
    "256k": "256",
    "192k": "192",
    "128k": "130",  # SomaFM uses 130 for 128k
    "96k": "96",
    "64k": "64",
    "32k": "32",
}

# Alternative mappings for flexibility (accept multiple patterns)
LABEL_TO_BITRATE_NUMS: Dict[str, List[str]] = {
    "128k": ["128", "130"],  # Accept both 128 and 130
    "320k": ["320"],
    "256k": ["256"],
    "192k": ["192"],
    "96k": ["96"],
    "64k": ["64"],
    "32k": ["32"],
}

# Format priority (mp3 preferred, then aac, then aacp)
FORMAT_PRIORITY: Dict[str, int] = {
    "mp3": 0,
    "aac": 1,
    "aacp": 2,
}

# Bitrate order for sorting (higher bitrate first)
BITRATE_ORDER: Dict[str, int] = {
    "320k": 0,
    "256k": 1,
    "192k": 2,
    "128k": 3,
    "96k": 4,
    "64k": 5,
    "32k": 6,
}


def extract_bitrate_from_url(url: str) -> str:
    """Extract bitrate label from URL.

    Searches URL for bitrate numbers and maps to standard label.
    Checks in descending order (320, 256, 192, etc.) to avoid false matches.

    Args:
        url: Stream or playlist URL

    Returns:
        Standard bitrate label (e.g., "128k") or "128k" as default
    """
    # Check for bitrate numbers in URL (order matters - check longer first)
    for num_str in ["320", "256", "192", "128", "96", "64", "32"]:
        if num_str in url:
            # Map to standard label
            num = int(num_str)
            return BITRATE_NUM_TO_LABEL.get(num, "128k")

    return "128k"


def extract_bitrate_from_playlist_filename(url: str) -> Optional[str]:
    """Extract bitrate label from playlist filename.

    Matches patterns like: bootliquor320.pls, beatblender130.pls, 7soul64.pls

    Args:
        url: Playlist URL

    Returns:
        Standard bitrate label or None if not found
    """
    match = re.search(r'(\d{2,3})\.pls$', url)
    if match:
        br_num = int(match.group(1))
        return map_bitrate_number_to_label(br_num)
    return None


def map_bitrate_number_to_label(br_num: int) -> str:
    """Map bitrate number to standard label.

    Args:
        br_num: Bitrate number from URL (e.g., 320, 130, 64)

    Returns:
        Standard bitrate label (e.g., "320k", "128k")
    """
    # Direct mapping
    if br_num in BITRATE_NUM_TO_LABEL:
        return BITRATE_NUM_TO_LABEL[br_num]

    # Fallback: map to nearest standard bitrate
    if br_num >= 256:
        return "320k"
    elif br_num >= 128:
        return "128k"
    elif br_num >= 64:
        return "64k"
    else:
        return "32k"


def map_label_to_bitrate_numbers(label: str) -> List[str]:
    """Map bitrate label to URL number patterns.

    Args:
        label: Standard bitrate label (e.g., "128k")

    Returns:
        List of number patterns to search for in URL
    """
    return LABEL_TO_BITRATE_NUMS.get(label, [LABEL_TO_BITRATE_NUM.get(label, "130")])


def get_bitrate_sort_key(bitrate_item: str) -> Tuple[int, int]:
    """Get sort key for bitrate item.

    Args:
        bitrate_item: Bitrate string in format "format:label" (e.g., "mp3:128k")

    Returns:
        Tuple of (format_priority, bitrate_priority) for sorting
    """
    if ":" in bitrate_item:
        fmt, br = bitrate_item.split(":")
    else:
        fmt = "mp3"
        br = bitrate_item

    format_priority = FORMAT_PRIORITY.get(fmt, 99)
    bitrate_priority = BITRATE_ORDER.get(br, 99)

    return (format_priority, bitrate_priority)


def normalize_bitrate_label(label: str) -> str:
    """Normalize bitrate label to standard format.

    Args:
        label: Bitrate label (may be non-standard)

    Returns:
        Normalized standard bitrate label
    """
    # Remove 'k' suffix if present for parsing
    clean_label = label.lower().rstrip('k')

    try:
        br_num = int(clean_label)
        return map_bitrate_number_to_label(br_num)
    except ValueError:
        # Return as-is with 'k' suffix if already a label
        return label if label.endswith('k') else f"{label}k"
