## 1. Rewrite resize_file

- [x] 1.1 Replace constants: `MAX_ITERATIONS=10`, `QUALITY=90`, `MIN_DIMENSION=64`, `TARGET_RATIO_LO=0.90`
- [x] 1.2 Implement informed initial guess: `scale = sqrt(max_size_bytes / original_size)` clamped to `[0.1, 1.0]`
- [x] 1.3 Implement binary search loop on scale factor with `lo=0.1`, `hi=1.0`, converging into the 90-100% target band
- [x] 1.4 Use fixed quality 90 for JPEG/WEBP, optimize-only for PNG (no quality iteration)
- [x] 1.5 Add minimum dimension guard at 64px (break search if either dimension would go below)
- [x] 1.6 Implement best-effort fallback: prefer best under-limit, then closest overall, then ValidationError

## 2. Test suite for image_size_utils

- [x] 2.1 Create `test/features/images/test_image_size_utils.py` with test class
- [x] 2.2 Test: under-limit file returns original path unchanged
- [x] 2.3 Test: large JPEG resized into 90-100% target band
- [x] 2.4 Test: large PNG resized into 90-100% target band
- [x] 2.5 Test: large WEBP resized into 90-100% target band
- [x] 2.6 Test: minimum dimension guard returns best effort without crashing
- [x] 2.7 Test: iteration safety cap returns best effort
- [x] 2.8 Test: `normalize_image_size_category` variants
- [x] 2.9 Test: `calculate_image_size_category` thresholds and error case

## 3. Verify

- [x] 3.1 Run existing tests to confirm no regressions
- [x] 3.2 Run pre-commit linting
