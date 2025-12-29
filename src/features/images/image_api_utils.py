import re
from dataclasses import dataclass, replace
from typing import IO

from features.external_tools.external_tool import ExternalTool, ToolType
from features.external_tools.external_tool_library import (
    GEMINI_2_5_FLASH_IMAGE,
    IMAGE_EDITING_FLUX_KONTEXT_PRO,
    IMAGE_EDITING_GOOGLE_NANO_BANANA,
    IMAGE_EDITING_GOOGLE_NANO_BANANA_PRO,
    IMAGE_EDITING_SEED_EDIT_3,
    IMAGE_GENERATION_EDITING_FLUX_2_MAX,
    IMAGE_GENERATION_EDITING_FLUX_2_PRO,
    IMAGE_GENERATION_EDITING_GPT_IMAGE_1_5,
    IMAGE_GENERATION_EDITING_SEEDREAM_4,
    IMAGE_GENERATION_FLUX_1_1,
    IMAGE_GENERATION_GEMINI_2_5_FLASH_IMAGE,
)
from util import log

VALID_ASPECT_RATIOS = [
    "9:16",  # Ultra-tall portrait
    "2:3",   # Tall portrait
    "3:4",   # Portrait
    "1:1",   # Square
    "4:3",   # Landscape
    "3:2",   # Wide landscape
    "16:9",  # Ultra-wide landscape
]


@dataclass(frozen = True)
class UnifiedImageParameters:
    # prompting
    prompt: str
    prompt_upsampling: bool = False
    enhance_prompt: bool = False
    # output
    aspect_ratio: str = "2:3"
    size: str = "2K"
    resolution: str | None = None
    image_size: str | None = None
    quality: str = "high"
    width: int | None = None
    height: int | None = None
    output_format: str = "png"
    output_mime_type: str = "image/png"
    output_quality: int = 90
    output_compression: int = 90
    background: str = "auto"
    # inference
    num_inference_steps: int = 30
    number_of_images: int = 1
    num_outputs: int = 1
    max_images: int = 1
    sequential_image_generation: str = "disabled"
    # safety
    moderation: str = "low"
    safety_tolerance: int = 1
    safety_filter_level: str = "block_only_high"
    # input
    input_fidelity: str = "high"
    guidance_scale: float = 5.5
    # file inputs
    image: IO[bytes] | None = None
    input_image: IO[bytes] | None = None
    image_input: list[IO[bytes]] | None = None
    input_images: list[IO[bytes]] | None = None


def map_to_model_parameters(
    tool: ExternalTool,
    prompt: str = "",
    aspect_ratio: str | None = None,
    size: str | None = None,
    input_files: list[IO[bytes]] | None = None,
) -> UnifiedImageParameters:
    log.d(f"Mapping image parameters for model '{tool.id}'")

    unified_params = UnifiedImageParameters(
        prompt = prompt,
        aspect_ratio = resolve_aspect_ratio(tool, aspect_ratio, input_files),
        size = size or "2K",
        image = input_files[0] if input_files else None,
        input_image = input_files[0] if input_files else None,
        image_input = input_files,
        input_images = input_files,
    )

    if tool == IMAGE_GENERATION_FLUX_1_1:
        return unified_params
    elif tool == IMAGE_GENERATION_EDITING_FLUX_2_PRO:
        return replace(unified_params, resolution = convert_size_to_mp(unified_params.size))
    elif tool == IMAGE_GENERATION_EDITING_FLUX_2_MAX:
        return replace(unified_params, resolution = convert_size_to_mp(unified_params.size))
    elif tool == IMAGE_EDITING_FLUX_KONTEXT_PRO:
        return unified_params
    elif tool == IMAGE_GENERATION_EDITING_GPT_IMAGE_1_5:
        return unified_params
    elif tool == IMAGE_EDITING_GOOGLE_NANO_BANANA:
        return unified_params
    elif tool == IMAGE_EDITING_GOOGLE_NANO_BANANA_PRO:
        return replace(unified_params, resolution = convert_size_to_k(unified_params.size))
    elif tool == IMAGE_EDITING_SEED_EDIT_3:
        return unified_params
    elif tool == IMAGE_GENERATION_EDITING_SEEDREAM_4:
        return replace(unified_params, size = convert_size_to_k(unified_params.size))
    elif tool == GEMINI_2_5_FLASH_IMAGE:
        return replace(unified_params, image_size = convert_size_to_k(unified_params.size))
    elif tool == IMAGE_GENERATION_GEMINI_2_5_FLASH_IMAGE:
        return replace(unified_params, image_size = convert_size_to_k(unified_params.size))
    else:
        log.w(f"Unknown model '{tool.id}', using default mapping")
        return unified_params


def resolve_aspect_ratio(
    tool: ExternalTool,
    aspect_ratio: str | None,
    input_files: list[IO[bytes]] | None = None,
) -> str:
    is_editing = ToolType.images_edit in tool.types and input_files
    log.t(f"Resolving aspect ratio for '{tool.id}'... is_editing: {is_editing}, requested: '{aspect_ratio}'")

    # no aspect ratio requested
    if not aspect_ratio:
        log.t("No aspect ratio requested, using default: 'match_input_image' if editing, '2:3' if generation")
        return "match_input_image" if is_editing else "2:3"
    cleaned = re.sub(r"\s+", "", aspect_ratio)

    # check if match_input_image is requested
    if cleaned == "match_input_image":
        if not is_editing:
            log.w(f"'match_input_image' not supported for '{tool.id}' (no input files or generation-only), using '2:3'")
            return "2:3"
        log.t("Using 'match_input_image' for editing, as requested")
        return cleaned

    # check if valid aspect ratio is requested
    if cleaned in VALID_ASPECT_RATIOS:
        log.t(f"Using valid aspect ratio '{cleaned}' as requested")
        return cleaned

    # check if invalid aspect ratio is requested
    try:
        parts = cleaned.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        input_ratio = float(parts[0]) / float(parts[1])
    except (ValueError, ZeroDivisionError):
        log.w(f"Invalid aspect ratio '{aspect_ratio}', using default")
        return "match_input_image" if is_editing else "2:3"

    # find the closest valid aspect ratio
    valid_float_ratios = []
    for ratio_str in VALID_ASPECT_RATIOS:
        parts = ratio_str.split(":")
        float_ratio = float(parts[0]) / float(parts[1])
        valid_float_ratios.append((float_ratio, ratio_str))
    closest_ratio_tuple = min(valid_float_ratios, key = lambda t: abs(t[0] - input_ratio))
    closest_ratio = closest_ratio_tuple[1]

    log.t(f"Using closest aspect ratio '{closest_ratio}'")
    return closest_ratio


def convert_size_to_mp(size: str) -> str:
    size_lower = size.lower()
    if size_lower.endswith(" mp"):
        return size
    if size_lower == "1k":
        return "1 MP"
    elif size_lower == "2k":
        return "2 MP"
    elif size_lower == "4k":
        return "4 MP"
    else:
        log.w(f"Unknown size format '{size}', defaulting to '2 MP'")
        return "2 MP"


def convert_size_to_k(size: str) -> str:
    size_lower = size.lower()
    if size_lower.endswith("k"):
        return size.upper()
    elif size_lower.endswith(" mp"):
        mp_value = size_lower.replace(" mp", "")
        if mp_value == "1":
            return "1K"
        elif mp_value == "2":
            return "2K"
        elif mp_value == "4":
            return "4K"
    log.w(f"Unknown size format '{size}', defaulting to '2K'")
    return "2K"
