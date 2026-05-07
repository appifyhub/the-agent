## 1. Dependencies and Assets

- [x] 1.1 Add `resvg-py` to `Pipfile` and run `pipenv install`
- [x] 1.2 Scout existing asset conventions; create `src/assets/fonts/` if not present
- [x] 1.3 Drop Heebo Variable TTF (from `~/Downloads/Heebo/Heebo-VariableFont_wght.ttf`) into the fonts directory and verify `OFL-Heebo-Variable.txt` is included for license compliance
- [x] 1.4 Fetch agent brand purple-blue hex values from `agent.appifyhub.com` and pin in a constants module (e.g., `src/features/social_cards/brand.py`)
- [x] 1.5 Create placeholder agent logo SVG and X icon SVG to use until real assets are provided

## 2. TwitterStatusFetcher Refactor (Structured Mode)

- [x] 2.1 Define a typed dataclass for the structured output covering user (name, handle, bio, profile_image_url), tweet (text, language, created_at), and media list (url, type, preview_image_url)
- [x] 2.2 Extend the X API request in `TwitterStatusFetcher` to include `profile_image_url` in `user.fields`, `created_at` in `tweet.fields`, and `preview_image_url` in `media.fields`
- [x] 2.3 Extract the API call + raw-dict caching into a private `__fetch_raw()` method, keyed under `twitter-status-fetcher-structured`
- [x] 2.4 Add public `as_structured()` method that returns the typed dataclass without invoking computer vision
- [x] 2.5 Add public `as_text()` method preserving the existing `execute()` text-formatting behavior (including CV photo descriptions); keep its existing cache untouched
- [x] 2.6 Update existing call sites (e.g., `WebFetcher`) to call `as_text()` instead of `execute()`; keep `execute()` as a thin alias for `as_text()` to avoid churn, OR update directly if call sites are few
- [x] 2.7 Add tests covering structured mode (with mocked X API response containing photos, GIF preview, and video preview) and verifying the structured cache key prefix

## 3. Photo Download and Theme Extraction

- [x] 3.1 Create `src/features/social_cards/photo_downloader.py` that downloads a list of image URLs (profile + media) to in-memory bytes; include bearer auth header support and verify on first integration test whether X CDN URLs require it
- [x] 3.2 Create `src/features/social_cards/theme.py` with a `pick_theme(profile_bytes, media_bytes_list, brand_default) -> ThemeColors` function implementing the three-tier fallback (profile dominant → combined media dominant → brand default)
- [x] 3.3 Implement dominant-color extraction using Pillow's `Image.quantize()` against a downsized image
- [x] 3.4 Implement gradient second-color derivation: ±10% lightness shift away from neutral, ±10° hue rotation toward red/blue
- [x] 3.5 Implement contrast-based foreground color choice (black or white) against the primary
- [x] 3.6 Add tests covering theme extraction priority, edge cases (no profile, no media, all-grayscale image), and gradient derivation

## 4. SVG Card Renderer

- [x] 4.1 Create `src/features/social_cards/card_layout.py` with constants for card width per aspect ratio (1080 / 1620), header height, padding, font sizes, and the photo-grid orientation rule
- [x] 4.2 Create `src/features/social_cards/card_template.py` (or a Jinja2 `.svg.j2` file) producing the full SVG: gradient background, header (circular avatar via `<clipPath>`, name+handle, datetime, agent logo), tweet text via `<text><tspan/></text>` with manual word-wrap, photo grid with selective corner rounding, and footer (X icon + shortened URL at low opacity)
- [x] 4.3 Implement word-wrap logic: measure text width per `<tspan>` and split tweet text into lines that fit the body width; expand the SVG `viewBox` height as the line count grows
- [x] 4.4 Implement photo-grid layout: portrait card → 1 col; landscape/square card → 2 col, downgraded to 1 col when ≥50% of photos are landscape
- [x] 4.5 Implement selective corner rounding using SVG `path` with per-corner radii (top corners on first row, bottom corners on last row)
- [x] 4.6 Embed photo bytes inline in the SVG as `data:image/...;base64,...` `<image>` href values
- [x] 4.7 Format the datetime as `YYYY-MM-DD · UTC h:mm AM/PM` from the X `created_at` ISO-8601 string
- [x] 4.8 Create `src/features/social_cards/card_renderer.py` with a `render(structured_data, theme, aspect_ratio) -> bytes` function that builds the SVG and rasterizes via `resvg-py`, ensuring the Heebo TTF is registered with the resvg font database
- [x] 4.9 Add unit tests for word-wrap, grid orientation rule, datetime formatting, and SVG-string snapshot of a known-input card

## 5. Renderer Orchestration

- [x] 5.1 Create `src/features/social_cards/social_card_orchestrator.py` that wires together: tweet ID resolution (`resolve_tweet_id`), structured fetch (`TwitterStatusFetcher.as_structured`), profile-image URL transform (`_normal` → `_bigger`), photo downloads, theme selection, URL shortening (`UrlShortener`), SVG render, and image upload (`ImageUploader`)
- [x] 5.2 Implement structured error handling: each failure point raises a `social_cards`-scoped error from `util.errors` with appropriate `util.error_codes`; the LLM tool layer surfaces these as JSON errors
- [x] 5.3 Add DI factory methods in `src/di/di.py` for `photo_downloader`, `social_card_orchestrator`, and any other new components
- [x] 5.4 Add tests covering the orchestrator's happy path, X API error, photo download error, render error, and upload error

## 6. LLM Tool Wiring

- [x] 6.1 Add `render_social_post(di, url, aspect_ratio)` function in `src/features/chat/llm_tools/llm_tool_library.py` with a generic docstring suitable for the LLM (e.g., "Renders a social network post (e.g., Twitter/X) into a styled, shareable card image. Returns the URL of the rendered image.")
- [x] 6.2 Default `aspect_ratio` to `"2:3"` and validate against the allowed set `{"1:1", "2:3", "3:2"}`; on invalid value, return error JSON
- [x] 6.3 Resolve the configured X API tool via `tool_choice_resolver.require_tool(ToolType.api_twitter, ...)` and pass it through to the orchestrator
- [x] 6.4 Register the new tool in `LLMToolLibrary.ALL_LLM_TOOLS`
- [x] 6.5 Add tests covering: success returns image URL in `__success({...})`, invalid URL returns error, invalid aspect_ratio returns error, downstream failure surfaces as error JSON

## 7. Documentation and Verification

- [x] 7.1 Update `docs/` with the new LLM tool entry (input args, return shape, example)
- [x] 7.2 Run `pipenv run pre-commit run --all-files --show-diff-on-failure` and resolve any lint issues
- [x] 7.3 Run the full test suite to confirm no regressions
- [x] 7.4 Manual end-to-end verification: invoke the tool against a real public tweet with photos and inspect the resulting card; verify against a tweet with a GIF, a video, and a no-media tweet
