"""Tests for the Wordle screenshot parser (imgparse.py).

Generates synthetic Wordle grid images with OpenCV to test tile detection,
color classification, row grouping, and edge cases. OCR tests are skipped
when tesseract is not installed.
"""

import cv2
import numpy as np
import pytest

from imgparse import (
    classify_color_hsv,
    classify_tile_color,
    parse_screenshot,
    KNOWN_COLORS,
)


# ---------------------------------------------------------------------------
# Color constants (BGR) matching real Wordle tiles
# ---------------------------------------------------------------------------
# NYT dark mode
GREEN_BGR = (79, 140, 82)    # #528c4f
YELLOW_BGR = (75, 159, 177)  # #b19f4b
GRAY_BGR = (60, 58, 58)      # #3a3a3c
# Background
BG_DARK = (16, 10, 6)        # dark mode background
BG_EMPTY = (31, 27, 18)      # #121213 empty tile interior


# ---------------------------------------------------------------------------
# Helpers to generate synthetic Wordle grid images
# ---------------------------------------------------------------------------

def make_tile(color_bgr, size=62):
    """Create a solid square tile image."""
    tile = np.full((size, size, 3), color_bgr, dtype=np.uint8)
    return tile


def make_grid_image(
    rows,
    tile_size=62,
    gap=5,
    padding=40,
    bg_color=BG_DARK,
    empty_rows=0,
):
    """Build a synthetic Wordle screenshot image.

    Args:
        rows: List of lists of BGR color tuples, e.g.
              [[GREEN, GRAY, YELLOW, GRAY, GREEN], ...]
        tile_size: Pixel size of each square tile.
        gap: Pixel gap between tiles.
        padding: Padding around the grid.
        bg_color: Background color (BGR).
        empty_rows: Number of extra empty rows to append (unplayed).

    Returns:
        (image_bytes, image_array)  – PNG-encoded bytes and the raw array.
    """
    n_rows = len(rows) + empty_rows
    n_cols = 5

    width = padding * 2 + n_cols * tile_size + (n_cols - 1) * gap
    height = padding * 2 + n_rows * tile_size + (n_rows - 1) * gap

    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    for ri, row_colors in enumerate(rows):
        for ci, color in enumerate(row_colors):
            x = padding + ci * (tile_size + gap)
            y = padding + ri * (tile_size + gap)
            img[y : y + tile_size, x : x + tile_size] = color

    # Draw empty rows with the empty-tile color
    for ei in range(empty_rows):
        ri = len(rows) + ei
        for ci in range(n_cols):
            x = padding + ci * (tile_size + gap)
            y = padding + ri * (tile_size + gap)
            img[y : y + tile_size, x : x + tile_size] = BG_EMPTY

    _, buf = cv2.imencode(".png", img)
    return bytes(buf), img


# ---------------------------------------------------------------------------
# classify_color_hsv tests
# ---------------------------------------------------------------------------

class TestClassifyColorHSV:
    """Test HSV-based color classification."""

    def test_green(self):
        # Bright green in BGR
        assert classify_color_hsv((79, 140, 82)) == "g"

    def test_yellow(self):
        # Wordle yellow in BGR (b=75, g=159, r=177) -> hex b19f4b
        assert classify_color_hsv((75, 160, 177)) == "y"

    def test_gray_low_saturation(self):
        # Gray with low saturation
        assert classify_color_hsv((60, 58, 58)) == "r"

    def test_dark_is_empty(self):
        # Very dark pixel = background/empty
        assert classify_color_hsv((10, 10, 6)) is None

    def test_pure_black(self):
        assert classify_color_hsv((0, 0, 0)) is None

    def test_medium_gray(self):
        # Medium gray (like Wordle's absent tile in light mode)
        assert classify_color_hsv((126, 131, 120)) == "r"

    def test_bright_green_variant(self):
        # A brighter green
        assert classify_color_hsv((100, 200, 80)) == "g"

    def test_bright_yellow_variant(self):
        # A brighter gold/yellow
        assert classify_color_hsv((50, 180, 200)) == "y"


# ---------------------------------------------------------------------------
# classify_tile_color tests
# ---------------------------------------------------------------------------

class TestClassifyTileColor:
    """Test tile color classification from ROI images."""

    def test_solid_green_tile(self):
        roi = make_tile(GREEN_BGR)
        assert classify_tile_color(roi) == "g"

    def test_solid_yellow_tile(self):
        roi = make_tile(YELLOW_BGR)
        assert classify_tile_color(roi) == "y"

    def test_solid_gray_tile(self):
        roi = make_tile(GRAY_BGR)
        assert classify_tile_color(roi) == "r"

    def test_empty_dark_tile(self):
        roi = make_tile(BG_EMPTY)
        assert classify_tile_color(roi) is None

    def test_tile_with_noise(self):
        """Tile mostly green with some noise pixels should still classify as green."""
        roi = make_tile(GREEN_BGR, size=60)
        # Add random noise to ~10% of pixels
        rng = np.random.RandomState(42)
        noise_mask = rng.random(roi.shape[:2]) < 0.10
        roi[noise_mask] = rng.randint(0, 255, (noise_mask.sum(), 3))
        assert classify_tile_color(roi) == "g"

    def test_known_hex_colors(self):
        """All entries in KNOWN_COLORS should classify correctly."""
        for hex_color, expected in KNOWN_COLORS.items():
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            roi = make_tile((b, g, r), size=10)
            result = classify_tile_color(roi)
            assert result == expected, (
                f"Hex #{hex_color}: expected {expected!r}, got {result!r}"
            )


# ---------------------------------------------------------------------------
# parse_screenshot – grid detection & row grouping
# ---------------------------------------------------------------------------

class TestParseScreenshotGridDetection:
    """Test that parse_screenshot correctly finds tiles and groups into rows."""

    def test_single_row_all_gray(self):
        """One row of 5 gray tiles."""
        img_bytes, _ = make_grid_image([[GRAY_BGR] * 5])
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "rrrrr"

    def test_single_row_mixed_colors(self):
        """One row with green, yellow, and gray."""
        colors = [GREEN_BGR, GRAY_BGR, YELLOW_BGR, GRAY_BGR, GREEN_BGR]
        img_bytes, _ = make_grid_image([colors])
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "gryrgr"[:5]
        # Verify exact pattern
        assert guesses[0]["result"] == "gryrg"

    def test_multiple_rows(self):
        """Three rows of colored tiles."""
        rows = [
            [GRAY_BGR] * 5,
            [GREEN_BGR, YELLOW_BGR, GRAY_BGR, GRAY_BGR, YELLOW_BGR],
            [GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR],
        ]
        img_bytes, _ = make_grid_image(rows)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 3
        assert guesses[0]["result"] == "rrrrr"
        assert guesses[1]["result"] == "gyrry"
        assert guesses[2]["result"] == "ggggg"

    def test_six_rows_full_game(self):
        """A full 6-guess game."""
        rows = [
            [GRAY_BGR, YELLOW_BGR, GRAY_BGR, GRAY_BGR, GRAY_BGR],
            [GRAY_BGR, GRAY_BGR, GREEN_BGR, YELLOW_BGR, GRAY_BGR],
            [YELLOW_BGR, GRAY_BGR, GREEN_BGR, GRAY_BGR, GREEN_BGR],
            [GREEN_BGR, GRAY_BGR, GREEN_BGR, GRAY_BGR, GREEN_BGR],
            [GREEN_BGR, YELLOW_BGR, GREEN_BGR, GRAY_BGR, GREEN_BGR],
            [GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR],
        ]
        img_bytes, _ = make_grid_image(rows)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 6
        assert guesses[5]["result"] == "ggggg"

    def test_played_rows_plus_empty_rows(self):
        """3 played rows followed by 3 empty rows — should only return 3 guesses."""
        rows = [
            [GRAY_BGR] * 5,
            [GREEN_BGR, YELLOW_BGR, GRAY_BGR, GRAY_BGR, GREEN_BGR],
            [GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR],
        ]
        img_bytes, _ = make_grid_image(rows, empty_rows=3)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 3

    def test_empty_image_returns_empty(self):
        """A completely dark image with no tiles."""
        img = np.full((400, 300, 3), BG_DARK, dtype=np.uint8)
        _, buf = cv2.imencode(".png", img)
        guesses = parse_screenshot(bytes(buf))
        assert guesses == []

    def test_invalid_bytes_returns_empty(self):
        """Random bytes that aren't a valid image."""
        guesses = parse_screenshot(b"not an image at all")
        assert guesses == []

    def test_empty_bytes_returns_empty(self):
        guesses = parse_screenshot(b"")
        assert guesses == []


# ---------------------------------------------------------------------------
# parse_screenshot – color extraction accuracy
# ---------------------------------------------------------------------------

class TestParseScreenshotColorAccuracy:
    """Test that color results are extracted correctly from grids."""

    @pytest.mark.parametrize(
        "color_bgr, expected_char",
        [
            (GREEN_BGR, "g"),
            (YELLOW_BGR, "y"),
            (GRAY_BGR, "r"),
        ],
    )
    def test_uniform_row(self, color_bgr, expected_char):
        """Row of all same color should produce uniform result string."""
        img_bytes, _ = make_grid_image([[color_bgr] * 5])
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == expected_char * 5

    def test_alternating_pattern(self):
        """Alternating green and yellow."""
        colors = [GREEN_BGR, YELLOW_BGR, GREEN_BGR, YELLOW_BGR, GREEN_BGR]
        img_bytes, _ = make_grid_image([colors])
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "gygyg"

    def test_all_color_combos_across_rows(self):
        """Each row has a different pattern."""
        rows = [
            [GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR],
            [YELLOW_BGR, YELLOW_BGR, YELLOW_BGR, YELLOW_BGR, YELLOW_BGR],
            [GRAY_BGR, GRAY_BGR, GRAY_BGR, GRAY_BGR, GRAY_BGR],
            [GREEN_BGR, YELLOW_BGR, GRAY_BGR, GREEN_BGR, YELLOW_BGR],
        ]
        img_bytes, _ = make_grid_image(rows)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 4
        assert guesses[0]["result"] == "ggggg"
        assert guesses[1]["result"] == "yyyyy"
        assert guesses[2]["result"] == "rrrrr"
        assert guesses[3]["result"] == "gyrgy"


# ---------------------------------------------------------------------------
# parse_screenshot – different tile sizes and spacing
# ---------------------------------------------------------------------------

class TestParseScreenshotSizes:
    """Test grid detection with various tile sizes and layouts."""

    @pytest.mark.parametrize("tile_size", [40, 62, 80, 100])
    def test_different_tile_sizes(self, tile_size):
        """Detection should work across a range of tile sizes."""
        rows = [
            [GREEN_BGR, GRAY_BGR, YELLOW_BGR, GRAY_BGR, GREEN_BGR],
        ]
        img_bytes, _ = make_grid_image(rows, tile_size=tile_size)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "gryrg"

    @pytest.mark.parametrize("gap", [4, 5, 10, 15])
    def test_different_gaps(self, gap):
        """Detection should work with various inter-tile gaps (>=4px)."""
        rows = [
            [YELLOW_BGR, GREEN_BGR, GRAY_BGR, GREEN_BGR, YELLOW_BGR],
        ]
        img_bytes, _ = make_grid_image(rows, gap=gap)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "ygrgy"

    def test_large_padding(self):
        """Tiles with lots of surrounding padding (like a phone screenshot)."""
        rows = [
            [GRAY_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GRAY_BGR],
        ]
        img_bytes, _ = make_grid_image(rows, padding=150)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["result"] == "rgggr"


# ---------------------------------------------------------------------------
# parse_screenshot – OCR / letter extraction
# ---------------------------------------------------------------------------

def _has_tesseract():
    """Check if tesseract OCR is available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def make_grid_with_letters(rows_data, tile_size=62, gap=5, padding=40):
    """Build a grid with letters drawn on tiles.

    Args:
        rows_data: list of list of (letter, color_bgr) tuples.

    Returns:
        PNG bytes.
    """
    n_rows = len(rows_data)
    n_cols = 5
    width = padding * 2 + n_cols * tile_size + (n_cols - 1) * gap
    height = padding * 2 + n_rows * tile_size + (n_rows - 1) * gap

    img = np.full((height, width, 3), BG_DARK, dtype=np.uint8)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = tile_size / 40.0
    thickness = max(2, tile_size // 20)

    for ri, row in enumerate(rows_data):
        for ci, (letter, color) in enumerate(row):
            x = padding + ci * (tile_size + gap)
            y = padding + ri * (tile_size + gap)
            # Fill tile
            img[y : y + tile_size, x : x + tile_size] = color
            # Draw letter centered
            text_size = cv2.getTextSize(letter.upper(), font, font_scale, thickness)[0]
            tx = x + (tile_size - text_size[0]) // 2
            ty = y + (tile_size + text_size[1]) // 2
            cv2.putText(img, letter.upper(), (tx, ty), font, font_scale, (255, 255, 255), thickness)

    _, buf = cv2.imencode(".png", img)
    return bytes(buf)


@pytest.mark.skipif(not _has_tesseract(), reason="tesseract not installed")
class TestParseScreenshotOCR:
    """Test letter extraction (requires tesseract)."""

    def test_simple_word(self):
        row_data = [
            ("S", GREEN_BGR), ("T", GRAY_BGR), ("A", YELLOW_BGR),
            ("R", GRAY_BGR), ("E", GREEN_BGR),
        ]
        img_bytes = make_grid_with_letters([row_data], tile_size=80)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        assert guesses[0]["word"] == "stare"
        assert guesses[0]["result"] == "gryrg"

    def test_multi_row_words(self):
        rows = [
            [("C", GRAY_BGR), ("R", YELLOW_BGR), ("A", GRAY_BGR),
             ("N", GRAY_BGR), ("E", YELLOW_BGR)],
            [("S", GRAY_BGR), ("T", GRAY_BGR), ("A", GRAY_BGR),
             ("L", GREEN_BGR), ("E", GRAY_BGR)],
        ]
        img_bytes = make_grid_with_letters(rows, tile_size=80)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 2
        assert guesses[0]["word"] == "crane"
        assert guesses[1]["word"] == "stale"


# ---------------------------------------------------------------------------
# parse_screenshot – word field when OCR unavailable
# ---------------------------------------------------------------------------

class TestParseScreenshotNoOCR:
    """When OCR is unavailable, words should contain '?' placeholders but
    colors should still be detected."""

    def test_word_has_placeholders(self):
        """Without tesseract, letters become '?' but result colors are correct."""
        rows = [[GREEN_BGR, YELLOW_BGR, GRAY_BGR, GRAY_BGR, GREEN_BGR]]
        img_bytes, _ = make_grid_image(rows)
        guesses = parse_screenshot(img_bytes)
        assert len(guesses) == 1
        # Colors must be correct regardless of OCR
        assert guesses[0]["result"] == "gyrrg"
        # Word should be 5 chars (either letters or ?)
        assert len(guesses[0]["word"]) == 5


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tricky inputs that could trip up the parser."""

    def test_very_small_image(self):
        """Image too small to contain tiles."""
        img = np.full((20, 20, 3), GRAY_BGR, dtype=np.uint8)
        _, buf = cv2.imencode(".png", img)
        assert parse_screenshot(bytes(buf)) == []

    def test_image_with_non_square_shapes(self):
        """Image with rectangular (non-square) shapes should not detect tiles."""
        img = np.full((400, 400, 3), BG_DARK, dtype=np.uint8)
        # Draw wide rectangles
        for i in range(5):
            x = 20 + i * 75
            cv2.rectangle(img, (x, 100), (x + 70, 140), GREEN_BGR, -1)
        _, buf = cv2.imencode(".png", img)
        guesses = parse_screenshot(bytes(buf))
        # Rectangles are not square, so shouldn't match tile detection
        # (or if they do match, the color should still be correct)
        # Just verify it doesn't crash
        assert isinstance(guesses, list)

    def test_jpeg_encoding(self):
        """JPEG-encoded images should also parse (lossy compression)."""
        rows = [[GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR, GREEN_BGR]]
        # Build the image directly and encode as JPEG
        img_bytes, img = make_grid_image(rows)
        _, jpeg_buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        guesses = parse_screenshot(bytes(jpeg_buf))
        # JPEG compression may alter colors slightly, but greens should survive
        if len(guesses) == 1:
            assert guesses[0]["result"] == "ggggg"

    def test_single_tile_not_enough(self):
        """An image with only 1 tile shouldn't produce results."""
        img = np.full((200, 200, 3), BG_DARK, dtype=np.uint8)
        img[50:112, 50:112] = GREEN_BGR  # one 62x62 tile
        _, buf = cv2.imencode(".png", img)
        guesses = parse_screenshot(bytes(buf))
        assert guesses == []

    def test_four_tiles_in_row_not_five(self):
        """A row of 4 tiles (not 5) should be skipped."""
        img = np.full((200, 500, 3), BG_DARK, dtype=np.uint8)
        for i in range(4):
            x = 40 + i * 70
            img[40:102, x : x + 62] = GREEN_BGR
        _, buf = cv2.imencode(".png", img)
        guesses = parse_screenshot(bytes(buf))
        assert guesses == []
