import re

VALID_ASPECT_RATIOS = [
    "9:16",  # Ultra-tall portrait
    "2:3",   # Tall portrait
    "3:4",   # Portrait
    "1:1",   # Square
    "4:3",   # Landscape
    "3:2",   # Wide landscape
    "16:9",  # Ultra-wide landscape
]


def validate_aspect_ratio(aspect_ratio: str | None, default: str) -> str:
    """Validates aspect ratio and returns valid value or closest match.

    If aspect_ratio is None, returns the default value.
    If aspect_ratio is valid (in VALID_ASPECT_RATIOS or default), returns it.
    If aspect_ratio is invalid, finds and returns the closest match by float ratio.
    Handles spaces in input (e.g., "2 : 3" becomes "2:3").

    Args:
        aspect_ratio: The aspect ratio to validate (e.g., "1:1", "2:3", or "2 : 3")
        default: The default value to use if aspect_ratio is None

    Returns:
        A valid aspect ratio string or the default value
    """
    if not aspect_ratio:
        return default

    # Remove all whitespace
    cleaned = re.sub(r"\s+", "", aspect_ratio)

    # Check if already valid
    if cleaned in VALID_ASPECT_RATIOS or cleaned == default:
        return cleaned

    # Try to find closest match by float ratio
    try:
        parts = cleaned.split(":")
        if len(parts) != 2:
            return default
        input_ratio = float(parts[0]) / float(parts[1])
    except (ValueError, ZeroDivisionError):
        return default

    # Calculate float ratios for all valid aspect ratios
    valid_float_ratios = []
    for ratio_str in VALID_ASPECT_RATIOS:
        parts = ratio_str.split(":")
        float_ratio = float(parts[0]) / float(parts[1])
        valid_float_ratios.append((float_ratio, ratio_str))

    # Find closest match by smallest arithmetic difference
    def distance_from_input(ratio_tuple: tuple[float, str]) -> float:
        float_ratio, _ = ratio_tuple
        return abs(float_ratio - input_ratio)

    closest_ratio_tuple = min(valid_float_ratios, key = distance_from_input)
    _, closest_ratio_str = closest_ratio_tuple
    return closest_ratio_str
