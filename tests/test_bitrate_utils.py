"""Tests for bitrate_utils module."""

import pytest

from somafm_tui.bitrate_utils import (
    BITRATE_LABELS,
    BITRATE_NUM_TO_LABEL,
    LABEL_TO_BITRATE_NUM,
    LABEL_TO_BITRATE_NUMS,
    FORMAT_PRIORITY,
    BITRATE_ORDER,
    extract_bitrate_from_url,
    extract_bitrate_from_playlist_filename,
    map_bitrate_number_to_label,
    map_label_to_bitrate_numbers,
    get_bitrate_sort_key,
    normalize_bitrate_label,
)


class TestConstants:
    """Tests for bitrate constants."""

    def test_bitrate_labels_ordered_descending(self):
        """Should have bitrate labels in descending order."""
        assert BITRATE_LABELS == ["320k", "256k", "192k", "128k", "96k", "64k", "32k"]

    def test_format_priority_mp3_first(self):
        """Should prioritize MP3 format."""
        assert FORMAT_PRIORITY["mp3"] < FORMAT_PRIORITY["aac"]
        assert FORMAT_PRIORITY["aac"] < FORMAT_PRIORITY["aacp"]

    def test_bitrate_order_descending(self):
        """Should have bitrate order from highest to lowest."""
        assert BITRATE_ORDER["320k"] < BITRATE_ORDER["256k"]
        assert BITRATE_ORDER["256k"] < BITRATE_ORDER["192k"]
        assert BITRATE_ORDER["128k"] < BITRATE_ORDER["96k"]


class TestExtractBitrateFromUrl:
    """Tests for extract_bitrate_from_url function."""

    def test_extracts_320k(self):
        """Should extract 320k from URL."""
        url = "https://somafm.com/dronezone320.pls"
        assert extract_bitrate_from_url(url) == "320k"

    def test_extracts_256k(self):
        """Should extract 256k from URL."""
        url = "https://somafm.com/beatblender256.pls"
        assert extract_bitrate_from_url(url) == "256k"

    def test_extracts_192k(self):
        """Should extract 192k from URL."""
        url = "https://somafm.com/groovesalad192.pls"
        assert extract_bitrate_from_url(url) == "192k"

    def test_extracts_128k_from_130(self):
        """Should map 130 to 128k (SomaFM convention)."""
        url = "https://somafm.com/dronezone130.pls"
        assert extract_bitrate_from_url(url) == "128k"

    def test_extracts_96k(self):
        """Should extract 96k from URL."""
        url = "https://somafm.com/spacestation96.pls"
        assert extract_bitrate_from_url(url) == "96k"

    def test_extracts_64k(self):
        """Should extract 64k from URL."""
        url = "https://somafm.com/secretagent64.pls"
        assert extract_bitrate_from_url(url) == "64k"

    def test_extracts_32k(self):
        """Should extract 32k from URL."""
        url = "https://somafm.com/lowfi32.pls"
        assert extract_bitrate_from_url(url) == "32k"

    def test_returns_default_when_no_bitrate(self):
        """Should return 128k as default when no bitrate found."""
        url = "https://somafm.com/playlist.pls"
        assert extract_bitrate_from_url(url) == "128k"

    def test_finds_bitrate_in_path(self):
        """Should find bitrate anywhere in URL path."""
        url = "https://ice1.somafm.com/dronezone-130-mp3"
        assert extract_bitrate_from_url(url) == "128k"


class TestExtractBitrateFromPlaylistFilename:
    """Tests for extract_bitrate_from_playlist_filename function."""

    def test_extracts_from_standard_filename(self):
        """Should extract bitrate from standard playlist filename."""
        url = "https://somafm.com/bootliquor320.pls"
        assert extract_bitrate_from_playlist_filename(url) == "320k"

    def test_extracts_130_as_128k(self):
        """Should map 130 to 128k."""
        url = "https://somafm.com/beatblender130.pls"
        assert extract_bitrate_from_playlist_filename(url) == "128k"

    def test_extracts_64k(self):
        """Should extract 64k from filename."""
        url = "https://somafm.com/7soul64.pls"
        assert extract_bitrate_from_playlist_filename(url) == "64k"

    def test_returns_none_when_no_match(self):
        """Should return None when no bitrate found."""
        url = "https://somafm.com/playlist.pls"
        assert extract_bitrate_from_playlist_filename(url) is None

    def test_ignores_non_pls_extension(self):
        """Should only match .pls extension."""
        url = "https://somafm.com/stream320.m3u"
        assert extract_bitrate_from_playlist_filename(url) is None


class TestMapBitrateNumberToLabel:
    """Tests for map_bitrate_number_to_label function."""

    def test_direct_mapping_320(self):
        """Should map 320 to 320k."""
        assert map_bitrate_number_to_label(320) == "320k"

    def test_direct_mapping_130_to_128k(self):
        """Should map 130 to 128k."""
        assert map_bitrate_number_to_label(130) == "128k"

    def test_direct_mapping_128_to_128k(self):
        """Should map 128 to 128k."""
        assert map_bitrate_number_to_label(128) == "128k"

    def test_direct_mapping_64(self):
        """Should map 64 to 64k."""
        assert map_bitrate_number_to_label(64) == "64k"

    def test_fallback_high_bitrate(self):
        """Should map unknown high bitrates to 320k."""
        assert map_bitrate_number_to_label(500) == "320k"

    def test_fallback_medium_bitrate(self):
        """Should map unknown medium bitrates to 128k."""
        assert map_bitrate_number_to_label(150) == "128k"

    def test_fallback_low_bitrate(self):
        """Should map unknown low bitrates to 32k."""
        assert map_bitrate_number_to_label(16) == "32k"


class TestMapLabelToBitrateNumbers:
    """Tests for map_label_to_bitrate_numbers function."""

    def test_128k_returns_both_128_and_130(self):
        """Should return both 128 and 130 for 128k."""
        numbers = map_label_to_bitrate_numbers("128k")
        assert "128" in numbers
        assert "130" in numbers

    def test_320k_returns_320(self):
        """Should return 320 for 320k."""
        numbers = map_label_to_bitrate_numbers("320k")
        assert numbers == ["320"]

    def test_64k_returns_64(self):
        """Should return 64 for 64k."""
        numbers = map_label_to_bitrate_numbers("64k")
        assert numbers == ["64"]

    def test_unknown_label_returns_default(self):
        """Should return default pattern for unknown label."""
        numbers = map_label_to_bitrate_numbers("unknown")
        assert isinstance(numbers, list)
        assert len(numbers) > 0


class TestGetBitrateSortKey:
    """Tests for get_bitrate_sort_key function."""

    def test_mp3_320k_has_highest_priority(self):
        """Should give highest priority to MP3 320k."""
        key = get_bitrate_sort_key("mp3:320k")
        assert key == (0, 0)

    def test_aac_320k_has_lower_format_priority(self):
        """Should give lower format priority to AAC."""
        mp3_key = get_bitrate_sort_key("mp3:320k")
        aac_key = get_bitrate_sort_key("aac:320k")
        
        assert mp3_key[0] < aac_key[0]

    def test_lower_bitrate_has_higher_number(self):
        """Should give higher numbers to lower bitrates."""
        high_key = get_bitrate_sort_key("mp3:320k")
        low_key = get_bitrate_sort_key("mp3:64k")
        
        assert high_key[1] < low_key[1]

    def test_parses_format_from_string(self):
        """Should parse format from bitrate string."""
        key = get_bitrate_sort_key("aacp:128k")
        assert key[0] == FORMAT_PRIORITY["aacp"]

    def test_defaults_to_mp3_when_no_format(self):
        """Should default to MP3 when no format specified."""
        key = get_bitrate_sort_key("128k")
        assert key[0] == FORMAT_PRIORITY["mp3"]


class TestNormalizeBitrateLabel:
    """Tests for normalize_bitrate_label function."""

    def test_already_normalized(self):
        """Should keep already normalized labels."""
        assert normalize_bitrate_label("128k") == "128k"
        assert normalize_bitrate_label("320k") == "320k"

    def test_removes_k_suffix_for_parsing(self):
        """Should handle labels with or without k suffix."""
        assert normalize_bitrate_label("128") == "128k"
        assert normalize_bitrate_label("320") == "320k"

    def test_maps_numbers_to_labels(self):
        """Should map bitrate numbers to standard labels."""
        assert normalize_bitrate_label("130") == "128k"
        assert normalize_bitrate_label("64") == "64k"

    def test_handles_unknown_gracefully(self):
        """Should handle unknown formats gracefully."""
        result = normalize_bitrate_label("unknown")
        assert isinstance(result, str)
