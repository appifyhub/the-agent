import io
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from util import log

MAX_ITERATIONS = 30


class ImageResizer:

    @staticmethod
    def __write_temp_file(content: bytes, suffix: str) -> str:
        with tempfile.NamedTemporaryFile(delete = False, suffix = suffix) as tmp:
            tmp.write(content)
            tmp.flush()
            return tmp.name

    def resize_file(self, input_path: str, max_size_bytes: int) -> str:
        try:
            original_size = Path(input_path).stat().st_size
            if original_size <= max_size_bytes:
                log.w("Image is within size limit, no resizing needed")
                return input_path

            with Image.open(input_path) as image:
                original_format = image.format or "PNG"
                log.t(f"Original image: {image.size}, format: {original_format}")

                # configure resizing parameters
                quality = 95
                quality_min = 85
                quality_step = 5
                scale_factor = 0.9
                scale_step = 0.02
                scale_min = 0.1
                best_under: bytes | None = None
                best_under_diff: float = float("inf")
                best_any: bytes | None = None
                best_any_diff: float = float("inf")
                suffix = Path(input_path).suffix or ".png"
                prev_diff: float | None = None

                # resize the image until it fits the size limit
                iteration = 0
                while True:
                    iteration += 1
                    if iteration >= MAX_ITERATIONS:
                        log.w("Max iterations reached, returning best effort")
                        if best_under is not None:
                            return ImageResizer.__write_temp_file(best_under, suffix)
                        if best_any is not None:
                            return ImageResizer.__write_temp_file(best_any, suffix)
                        raise ValueError(f"Could not resize image to acceptable size in {MAX_ITERATIONS} iterations")
                    log.d(f"Resizing in iteration {iteration}, scale_factor: {scale_factor}, quality: {quality}")

                    output = io.BytesIO()
                    current_image = image.copy()

                    # run the basic resizing operation
                    width, height = current_image.size
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)

                    if new_width < 32 or new_height < 32:
                        log.w("Image became too small during resizing, using best effort")
                        if best_under is not None:
                            return ImageResizer.__write_temp_file(best_under, suffix)
                        if best_any is not None:
                            return ImageResizer.__write_temp_file(best_any, suffix)
                        raise ValueError("Could not resize image to acceptable size")

                    current_image = current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # compute the format and quality metadata
                    save_format = original_format
                    if save_format not in ["JPEG", "PNG", "WEBP"]:
                        save_format = "PNG"
                    is_lossless = save_format == "PNG"

                    save_kwargs: dict[str, Any] = {"format": save_format}
                    if save_format == "JPEG":
                        save_kwargs["quality"] = quality
                        save_kwargs["optimize"] = True
                    elif save_format == "PNG":
                        save_kwargs["optimize"] = True
                    elif save_format == "WEBP":
                        save_kwargs["quality"] = quality

                    current_image.save(output, **save_kwargs)
                    output_size = output.tell()

                    output_mb = output_size / 1024 / 1024
                    log.t(f"Resized to {current_image.size}, size: {output_mb:.2f} MB, quality: {quality}")

                    output.seek(0)
                    output_bytes = output.read()

                    # check the result to see if it's the best so far
                    diff = abs(output_size - max_size_bytes)
                    if output_size <= max_size_bytes and diff < best_under_diff:
                        best_under_diff = diff
                        best_under = output_bytes
                    if diff < best_any_diff:
                        best_any_diff = diff
                        best_any = output_bytes

                    # if the result is within the size limit, return it
                    if output_size <= max_size_bytes:
                        if output_size >= max_size_bytes * 0.97:
                            original_mb = original_size / 1024 / 1024
                            log.i(
                                f"Successfully resized image from {original_mb:.2f} MB to "
                                f"{output_mb:.2f} MB (within 3% margin)",
                            )
                            return ImageResizer.__write_temp_file(output_bytes, suffix)
                        if prev_diff is not None and diff > prev_diff:
                            log.t("Diff started increasing below target; returning best under-limit")
                            if best_under is not None:
                                return ImageResizer.__write_temp_file(best_under, suffix)
                            if best_any is not None:
                                return ImageResizer.__write_temp_file(best_any, suffix)
                            return ImageResizer.__write_temp_file(output_bytes, suffix)

                    # if the result is not within the size limit, adjust the parameters and loop again
                    if (not is_lossless) and quality > quality_min + quality_step:
                        quality -= quality_step
                    else:
                        scale_factor -= scale_step
                    prev_diff = diff

                    # check if the parameters are too small to continue
                    if scale_factor <= scale_min or quality <= quality_min:
                        log.w("Could not resize image to fit size limit closely, returning best effort")
                        if best_under is not None:
                            return ImageResizer.__write_temp_file(best_under, suffix)
                        if best_any is not None:
                            return ImageResizer.__write_temp_file(best_any, suffix)
                        return ImageResizer.__write_temp_file(output_bytes, suffix)
        except Exception as e:
            log.e("Failed to resize image", e)
            raise
