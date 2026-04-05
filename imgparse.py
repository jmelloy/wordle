"""Parse Wordle screenshots to extract guesses and color results.

Uses OpenCV for grid detection and color classification, plus
pytesseract for OCR of individual tile letters.
"""

import cv2
import numpy as np
from collections import Counter, defaultdict

# Known Wordle tile colors (BGR hex → semantic)
# Covers common dark-mode Wordle variants (NYT, iPhone, Android, Mac)
KNOWN_COLORS = {
    # Greens
    "528c4f": "g", "608b55": "g", "618c55": "g",
    "6aaa64": "g", "538d4e": "g", "569b4a": "g",
    # Yellows
    "b19f4b": "y", "b1a04c": "y", "b59f3b": "y",
    "c9b458": "y", "b5a33b": "y",
    # Grays / reds (absent)
    "3a3a3c": "r", "787c7e": "r", "818384": "r",
    "58595a": "r", "838384": "r",
    # Background / empty (not a played tile)
    "121214": None, "121213": None, "1b1b1f": None,
    "2b2c36": None, "1a1a1b": None, "ffffff": None,
    "d3d6da": None, "878a8c": None,
}

# HSV-based fallback ranges for color classification
# (hue_low, hue_high, sat_min, val_min) → result char
HSV_RANGES = [
    # Green: hue ~35-85
    (35, 85, 50, 50, "g"),
    # Yellow/orange: hue ~15-35
    (15, 35, 50, 50, "y"),
    # Gray (absent): low saturation
    (0, 180, 0, 30, "r"),
]


def classify_color_hsv(bgr_tuple):
    """Classify a BGR color tuple using HSV ranges."""
    pixel = np.uint8([[list(bgr_tuple)]])
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])

    # Very dark = empty/background
    if v < 40:
        return None

    # Low saturation = gray (absent)
    if s < 40 and v > 40:
        return "r"

    # Green
    if 35 <= h <= 85 and s > 50:
        return "g"

    # Yellow
    if 15 <= h <= 35 and s > 50:
        return "y"

    # Default to red/gray for anything else with moderate value
    if v > 40:
        return "r"

    return None


def classify_tile_color(roi_image):
    """Classify a tile's color from its ROI image.

    First tries exact hex match against known colors, then
    falls back to HSV-based classification.
    """
    pixels = roi_image.reshape(-1, 3)
    pixel_counts = Counter(map(tuple, pixels))
    b, g, r = pixel_counts.most_common(1)[0][0]
    hex_color = f"{r:02x}{g:02x}{b:02x}"

    if hex_color in KNOWN_COLORS:
        return KNOWN_COLORS[hex_color]

    return classify_color_hsv((b, g, r))


def ocr_tile_letter(gray_tile):
    """Extract a single letter from a grayscale tile image using OCR."""
    try:
        import pytesseract
        # Threshold for clean OCR
        _, thresh = cv2.threshold(gray_tile, 160, 255, cv2.THRESH_BINARY_INV)
        text = pytesseract.image_to_string(
            thresh,
            config="--psm 10 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            lang="eng",
        ).strip()
        if text and text[0].isalpha():
            return text[0].lower()
    except ImportError:
        pass
    return None


def fallback_ocr_row(gray_image, tiles_in_row):
    """Try OCR on a full row if individual tile OCR failed."""
    try:
        import pytesseract
        if not tiles_in_row:
            return None
        xs = [t["x"] for t in tiles_in_row]
        ys = [t["y"] for t in tiles_in_row]
        ws = [t["w"] for t in tiles_in_row]
        hs = [t["h"] for t in tiles_in_row]
        x1, y1 = min(xs), min(ys)
        x2 = max(x + w for x, w in zip(xs, ws))
        y2 = max(y + h for y, h in zip(ys, hs))
        row_img = gray_image[y1:y2, x1:x2]
        _, thresh = cv2.threshold(row_img, 160, 255, cv2.THRESH_BINARY_INV)
        text = pytesseract.image_to_string(
            thresh,
            config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            lang="eng",
        ).strip()
        if text and len(text) >= 5:
            return text[:5].lower()
    except ImportError:
        pass
    return None


def parse_screenshot(image_bytes):
    """Parse a Wordle screenshot and extract guesses with results.

    Args:
        image_bytes: Raw image file bytes (PNG, JPEG, etc.)

    Returns:
        List of dicts: [{"word": "arose", "result": "gyrrr"}, ...]
        Returns empty list if parsing fails.
    """
    # Decode image
    if not image_bytes:
        return []
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Find contours to locate tiles
    blur = cv2.medianBlur(gray, 5)
    sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpen = cv2.filter2D(blur, -1, sharpen_kernel)
    contours, _ = cv2.findContours(sharpen, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # Find square-ish contours that could be tiles
    # Group by area to find the most common tile size
    area_counts = Counter()
    tile_candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        aspect = w / h if h > 0 else 0
        # Tiles are roughly square
        if 0.8 <= aspect <= 1.25 and area > 400:
            area_bucket = round(area, -2)  # bucket by hundreds
            area_counts[area_bucket] += 1
            tile_candidates.append((x, y, w, h, area, area_bucket))

    if not tile_candidates:
        return []

    # Find the dominant tile size (should appear in multiples of 5)
    # Pick the area bucket with count closest to a multiple of 5 and >= 5
    best_bucket = None
    best_score = -1
    for bucket, count in area_counts.most_common():
        if count >= 5:
            # Score: prefer counts that are multiples of 5, and larger counts
            remainder = count % 5
            score = count * 10 - remainder * 3
            if score > best_score:
                best_score = score
                best_bucket = bucket

    if best_bucket is None:
        return []

    # Filter to tiles matching the dominant size (within 25%)
    target_area = best_bucket
    tolerance = target_area * 0.25
    raw_tiles = []
    for x, y, w, h, area, bucket in tile_candidates:
        if abs(area - target_area) <= tolerance:
            raw_tiles.append({"x": x, "y": y, "w": w, "h": h})

    if len(raw_tiles) < 5:
        return []

    # Deduplicate overlapping contours (inner/outer edges of same tile).
    # Merge tiles whose centers are within half a tile width of each other,
    # keeping the larger one.
    raw_tiles.sort(key=lambda t: -(t["w"] * t["h"]))  # largest first
    tiles = []
    for t in raw_tiles:
        cx = t["x"] + t["w"] / 2
        cy = t["y"] + t["h"] / 2
        merge_dist = t["w"] * 0.5
        duplicate = False
        for kept in tiles:
            kcx = kept["x"] + kept["w"] / 2
            kcy = kept["y"] + kept["h"] / 2
            if abs(cx - kcx) < merge_dist and abs(cy - kcy) < merge_dist:
                duplicate = True
                break
        if not duplicate:
            tiles.append(t)

    if len(tiles) < 5:
        return []

    # Sort tiles into rows by y-coordinate, then by x within each row
    tiles.sort(key=lambda t: t["y"])

    # Group into rows (tiles in same row have similar y)
    rows = []
    current_row = [tiles[0]]
    for t in tiles[1:]:
        if abs(t["y"] - current_row[0]["y"]) < current_row[0]["h"] * 0.5:
            current_row.append(t)
        else:
            rows.append(sorted(current_row, key=lambda t: t["x"]))
            current_row = [t]
    rows.append(sorted(current_row, key=lambda t: t["x"]))

    # Only keep rows with exactly 5 tiles (standard Wordle grid)
    rows = [r for r in rows if len(r) == 5]

    if not rows:
        return []

    # Extract letters and colors from each tile
    guesses = []
    for row in rows:
        word = []
        result = []
        has_played_tile = False

        for tile in row:
            x, y, w, h = tile["x"], tile["y"], tile["w"], tile["h"]
            roi = image[y:y+h, x:x+w]
            gray_tile = gray[y:y+h, x:x+w]

            color = classify_tile_color(roi)
            if color is None:
                # Empty/unplayed tile - skip this row
                break

            has_played_tile = True
            result.append(color)

            letter = ocr_tile_letter(gray_tile)
            word.append(letter or "?")

        if not has_played_tile or len(result) != 5:
            continue

        word_str = "".join(word)

        # Try row-level OCR if any letters failed
        if "?" in word_str:
            row_text = fallback_ocr_row(gray, row)
            if row_text and len(row_text) == 5:
                word_str = row_text

        guesses.append({
            "word": word_str,
            "result": "".join(result),
        })

    return guesses
