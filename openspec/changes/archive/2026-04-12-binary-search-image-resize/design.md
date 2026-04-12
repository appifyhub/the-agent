## Context

`resize_file` in `src/features/images/image_size_utils.py` is called from `platform_bot_sdk.py` when a downloaded image exceeds the platform's size limit. The current implementation uses a linear walk-down: first reducing JPEG quality (95→85 in steps of 5), then reducing scale factor (0.9→0.1 in steps of 0.02). Each iteration performs a full PIL resize + encode. For a 20 MB image targeting 5 MB, this can take 15-20 iterations.

The function's public contract is simple: `(input_path, max_size_bytes) → output_path`. No callers depend on internal behavior — only that the returned file is under the limit.

## Goals / Non-Goals

**Goals:**

- Reduce iteration count from ~20 to ~7 for typical large-photo resizing
- Land output size in a predictable target band (90-100% of limit)
- Maintain the same public API (`resize_file(input_path, max_size_bytes) → str`)
- Add test coverage for `resize_file` and other untested functions in the module

**Non-Goals:**

- Changing the image format handling (PNG/JPEG/WEBP support stays the same)
- Optimizing PIL operations themselves (resize + encode are the fixed cost per iteration)
- Supporting additional output formats
- Changing the caller in `platform_bot_sdk.py`

## Decisions

### Binary search on scale factor with informed initial guess

The core change. Instead of decrementing scale by a fixed step, binary search between `lo=0.1` and `hi=1.0`. Start with `guess = sqrt(max_size_bytes / original_size)` clamped to `[0.1, 1.0]`.

**Why sqrt**: File size scales roughly with pixel area (width × height), and area scales with the square of the scale factor. So `sqrt(target_ratio)` gives a good first approximation.

**Alternative considered**: Linear search with adaptive step size. Rejected because binary search is simpler, converges faster, and doesn't require tuning step parameters.

### Fixed quality at 90 for lossy formats

JPEG/WEBP quality fixed at 90 instead of iterating from 95→85. Quality 90 is visually near-lossless while providing significant compression. This eliminates the quality iteration phase entirely and keeps dimensions as large as possible.

**Alternative considered**: Binary search on both quality and scale simultaneously. Rejected because it adds complexity with minimal benefit — quality 90 is the right tradeoff for chat-context images, and a single fixed value keeps the algorithm one-dimensional.

### Target band: 90-100% of max_size_bytes

Accept results where `max_size_bytes * 0.90 <= output_size <= max_size_bytes`. This gives a 10% wide band — wide enough for binary search to land in within ~7 iterations, tight enough to not waste space.

**Previous behavior**: Accepted anything under limit, but preferred within 3%. The new band is wider on the low end (10% vs 3%) which allows faster convergence.

### MAX_ITERATIONS = 10, MIN_DIMENSION = 64

Binary search on `[0.1, 1.0]` converges to 1% precision in `log2(0.9/0.01) ≈ 6.6` iterations. Cap at 10 as a safety net — should never trigger in practice. Minimum dimension raised from 32px to 64px since anything smaller is useless in a chat context.

### Best-effort fallback strategy

Track the best under-limit result seen during the search. If the loop exits without landing in the target band (due to iteration cap or minimum dimension), return the best under-limit result. If nothing was under the limit, return the closest result overall. Only raise `ValidationError` if no result was produced at all.

## Risks / Trade-offs

- **PNG compression unpredictability**: PNG file size depends heavily on image content (gradients compress well, noise doesn't). Binary search may take more iterations for PNG than JPEG. → Mitigation: the 10% wide target band and 10-iteration cap handle this; worst case returns best effort.
- **Quality 90 may over-compress for some use cases**: Fixed quality means no adaptation to image content. → Mitigation: 90 is the standard web-quality sweet spot; for chat-context images this is more than sufficient.
- **Informed guess assumes quadratic relationship**: The `sqrt` estimate is approximate — actual compression ratios vary by content. → Mitigation: it's just the starting point; binary search corrects from there regardless of guess accuracy.
