## Why

The current image resizing algorithm in `image_size_utils.py` uses a linear walk-down approach: it decreases JPEG quality in fixed steps (95 to 85), then decreases scale factor by 0.02 per iteration. For large photos needing significant size reduction, this burns 15-20+ iterations — each doing a full resize + encode cycle. A binary search approach converges logarithmically, reducing this to ~7 iterations.

## What Changes

- Replace the linear iterative resizing loop in `resize_file` with a binary search on scale factor
- Use an informed initial guess (`sqrt(target / original_size)`) to start near the right answer
- Fix compression quality at 90 for lossy formats (JPEG/WEBP) instead of iterating quality
- Target band of 90-100% of `max_size_bytes` (previously accepted anything under limit, preferring within 3%)
- Increase minimum dimension guard from 32px to 64px
- Reduce `MAX_ITERATIONS` from 30 to 10 (binary search converges in ~7)
- Add comprehensive test coverage for `resize_file` and other untested functions in the module

## Capabilities

### New Capabilities

- `binary-search-resize`: Binary search image resizing algorithm with informed initial guess, fixed quality, and target band convergence

### Modified Capabilities

## Impact

- `src/features/images/image_size_utils.py` — rewrite of `resize_file` function (public API unchanged)
- `test/features/images/test_image_size_utils.py` — new test file
- No API changes, no dependency changes, no breaking changes
- Callers (`platform_bot_sdk.py`) unaffected — same function signature, same return type
