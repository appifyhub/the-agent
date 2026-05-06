## Context

The codebase already has the building blocks for a tweet-to-card pipeline:

- `TwitterStatusFetcher` calls the X API v2, caches the result for 52 weeks, and currently flattens it into a text blob (with computer-vision photo descriptions inline).
- `WebFetcher` auto-routes Twitter URLs to that fetcher when the LLM calls `fetch_web_content`.
- `ImageUploader` posts binary image bytes to imgbb and returns a URL — the same return-shape the new tool will use.
- `UrlShortener` shortens any long URL to a slug for the card footer.
- `tool_choice_resolver` resolves `ToolType.api_twitter` to a `ConfiguredTool` with the X bearer.
- `ImageDraw`/Pillow is available, but no HTML/SVG renderer is.

What's missing: a structured-data path out of the fetcher (the current text path runs CV per photo, which we don't need for a card with embedded photos), an SVG-based card renderer, and the LLM tool binding.

The card design is a fixed-template layout with three blocks: header (circular avatar + name/handle/datetime + agent logo), tweet text (auto-wrapped), and a photo grid (max 4 in a 2×2 with selective corner rounding). A subtle footer with X icon and a shortened original URL closes the card. Theme is a linear gradient driven by the dominant color of the profile photo, with documented fallbacks.

## Goals / Non-Goals

**Goals:**

- An LLM-callable tool `render_social_post(url, aspect_ratio)` that returns a hosted PNG URL of a card-styled tweet.
- Reuse the X API call and its 52-week cache; no duplicate API hits when both text and structured paths are exercised on the same tweet.
- Reasonable rendering quality: anti-aliased text and corners, real gradients, embedded photos, no browser engine, no system dependencies on the host.
- Forward-compatible naming so the same tool can later cover other social platforms (Mastodon, Bluesky, etc.) without renaming.

**Non-Goals:**

- Decoding GIFs or sampling videos. We only render the X-supplied `preview_image_url` poster frame.
- Generating multiple cards per call, threading, or quote-tweets. One URL → one card.
- Replacing or deprecating the text path through `fetch_web_content`; both paths exist side by side.
- Persistent storage of rendered cards. The card lives long enough for the chat platform to consume it; messenger apps persist the file on their end.
- A pluggable render-strategy abstraction. We start with one renderer (resvg) and one source (X). Generalize later if a real second case appears.

## Decisions

### 1. SVG → PNG via `resvg-py`, not Pillow-only or HTML/CSS

**Decision:** Build a card SVG (Jinja2 or f-string template), rasterize via `resvg-py`.

**Why:** Anti-aliased rounded corners, drop shadows, linear gradients, multi-line text via `<tspan>`, and circular profile crops via `<clipPath>` are all native SVG primitives. `resvg-py` ships pre-built `manylinux_2_17_x86_64` wheels, has zero system dependencies, and produces reproducible cross-platform output (matters for testing).

**Alternatives considered:**
- *Pillow-only*: Possible, but rounded corners need supersampling (render at 2–4× and downscale), drop shadows need manual blur compositing, gradients need per-row fills, and multi-line text needs hand-rolled word wrapping. ~5× more code than the SVG path, and quality depends on the supersampling factor.
- *Playwright (headless Chromium)*: Best HTML/CSS fidelity but adds ~150–300 MB to the container, plus per-request browser startup latency. Overkill for one fixed template.
- *cairosvg*: Equally good rendering, but requires `libcairo2` system package. Trivial on Linux but adds a non-Python dep to the Dockerfile.
- *weasyprint / imgkit / wkhtmltopdf*: All require system packages and target PDF first; PNG output is secondary. CSS support is older or partial.

### 2. Structured-mode on the existing fetcher, not a separate fetcher

**Decision:** Refactor `TwitterStatusFetcher` so the X API call and result-caching live below the text-formatting step. Expose two read methods: `as_text()` (current behavior, with CV) and `as_structured()` (new, no CV; returns a typed dataclass/dict).

**Why:** The expensive part of fetching a tweet is the X API call plus CV per photo. The text path needs CV; the card path doesn't (we embed actual photos). Separating "fetch + cache raw" from "format" lets both modes share the API call and the cache. Adds one dataclass, no duplicated code.

**Alternative considered:** Build a parallel `TwitterStatusDataFetcher` that hits the API independently. Rejected — duplicates the cache logic, doubles the API rate-limit footprint, and drifts over time.

**Cache key strategy:** The current text cache stores formatted strings under `twitter-status-fetcher` and includes CV results. The structured cache stores the raw API JSON dict (no CV) under `twitter-status-fetcher-structured`. Two distinct keys because the values are fundamentally different shapes. The text path's cache is untouched; existing entries remain valid.

### 3. Aspect ratio is a target, not a hard clamp

**Decision:** The LLM passes `aspect_ratio: "1:1" | "2:3" | "3:2"` (default `"2:3"`). It determines:

- Card width: 1080 (portrait/square), 1620 (landscape).
- Minimum height: `width × (numerator / denominator inverted as appropriate for orientation)`.
- Photo-grid branch: portrait → 1 column; landscape/square → 2 columns, downgraded to 1 if ≥50% of photos are landscape.

Actual rendered height is `max(target_height, content_driven_height)`. Long tweets and tall photo stacks expand the card vertically. The chat-side photo-sending pipeline resizes the final asset, so we don't need to clamp.

**Why:** Hard-clamping height truncates tweet text or photos. A target gives the LLM control over visual emphasis (vertical for stories-style sharing, landscape for desktop chats) without breaking long content.

### 4. Theme color extraction priority

**Decision:** Three-tier fallback:

1. Dominant color of the profile photo (downloaded once, computed via `Image.quantize()`).
2. Combined dominant color of media photos (concatenate downsized versions, quantize once).
3. Agent brand purple-blue, fetched at first use from `agent.appifyhub.com` and pinned in code.

Then derive a gradient: second stop = first stop with ±10% lightness shift (away from neutral — bright stays bright direction, dark goes darker) and ±10° hue rotation toward red/blue (whichever the original is closer to). Text color = black or white by contrast against the dominant color.

**Why:** Profile photos are present on every tweet; media photos are sometimes absent. Brand fallback ensures a usable card even with a default avatar. Pillow's `Image.quantize()` covers dominant-color extraction without a new dependency.

### 5. Footer is a brand-light element, not a CTA

**Decision:** Bottom-of-card row with X icon (subtle SVG glyph) + shortened original URL via `UrlShortener`, both at low opacity. No "Open in X" button.

**Why:** The card's purpose is sharing, not driving traffic. The shortened URL gives provenance without competing with the tweet content visually.

### 6. Photo limits and media variants

**Decision:** Render at most 4 media items (X enforces this — 4 photos OR 1 GIF OR 1 video, never mixed). For animated GIFs and videos, pull `media.preview_image_url` from the X API response; treat them as still images. No play-button overlay, no inline indication that it's a moving format.

**Why:** Matches the X media model. The user explicitly opted out of an overlay for visual cleanliness.

### 7. Profile image variant: `_bigger` (73×73)

**Decision:** Transform the X-returned `profile_image_url` from `_normal` (48×48) to `_bigger` (73×73) via simple string replacement. Render in a 64-ish px circular crop.

**Why:** `_bigger` is the closest official variant to a clean rendering size. `original` (no suffix) returns full-size and is overkill for a thumb-style avatar. `_400x400` is not an official variant per X docs.

### 8. Failure mode is structured error, not text fallback

**Decision:** If any step fails (URL doesn't resolve to a tweet, API call errors, photo download fails, render fails, upload fails), the tool returns a JSON error to the LLM. It does not fall back to returning the tweet's text content.

**Why:** Keeps the tool contract crisp. The LLM can re-attempt by calling `fetch_web_content` if it wants the text. Mixing modes inside a single tool blurs intent.

## Risks / Trade-offs

- **Risk:** `resvg-py` doesn't support every SVG filter primitive. → **Mitigation:** Constrain the template to widely-supported primitives (linearGradient, clipPath, feGaussianBlur, basic text). If a real gap appears, fall back to `cairosvg` (drop-in API, costs `libcairo2` in the container).
- **Risk:** X media URLs may require authentication in some tenants. → **Mitigation:** The Twitter tool already holds a bearer; the photo-downloader can pass `Authorization: Bearer …` if needed. Verify on first integration test; if public works, skip the header.
- **Risk:** Long tweets push the card very tall, breaking the chat platform's preview crop. → **Mitigation:** This is the explicit design choice (content beats layout). If a chat platform truncates badly in practice, we can introduce a soft max-height with a "..." overflow later.
- **Risk:** Dominant-color extraction on busy photos produces ugly themes. → **Mitigation:** Quantize to a small palette (e.g., 8 colors) and pick the most-saturated rather than the most-frequent. Tune at implementation time against real samples.
- **Risk:** Heebo variable font rendering differences across resvg versions. → **Mitigation:** Pin `resvg-py` version; treat font rendering as part of the regression surface (snapshot tests if we add visual tests later).
- **Risk:** New cache prefix means double cache footprint per tweet (text + structured). → **Acceptable.** The cache TTL is 52 weeks but values are small JSON; storage cost is negligible compared to the API rate-limit savings.
- **Trade-off:** Adding a third dependency (`resvg-py`) for one feature. → **Accepted.** The cost of writing a Pillow-based renderer is higher in code, fragility, and maintenance than the cost of one well-maintained pip wheel.

## Migration Plan

1. Add `resvg-py` to `Pipfile`, run `pipenv install`.
2. Drop Heebo TTF under `src/assets/fonts/` (path scouted from existing project asset conventions).
3. Refactor `TwitterStatusFetcher`: extract API+cache into a private `__fetch_raw()`, add `as_text()` (current behavior) and `as_structured()` (new) public methods. Existing call sites continue to work via `as_text()` shim or rename.
4. Add structured-mode cache under new prefix; existing text-mode cache untouched.
5. Build `social_cards/` module: theme extraction, SVG template, photo download, renderer, top-level orchestrator.
6. Wire `render_social_post` into `llm_tool_library.py` and the `LLMToolLibrary.ALL_LLM_TOOLS` registry.
7. Wire DI factory in `di/di.py` for the renderer and orchestrator.
8. No DB migrations; no API contract changes.

**Rollback:** This is purely additive. To roll back, remove the new tool from the LLM registry and revert the structured-mode method. The text path is unchanged throughout.

## Open Questions

- **Agent + X logo SVG URLs**: User will supply real URLs. Until then, ship placeholder SVGs (single-letter monogram for agent, simple "X" glyph for the X icon) so the renderer is end-to-end testable.
- **Brand purple-blue hex values**: Fetch from `agent.appifyhub.com` at implementation time and pin in a constants module.
- **Font asset path**: Confirm whether the project already has a fonts/assets directory; otherwise create `src/assets/fonts/`.
- **Expiration of uploaded card**: Default `ImageUploader` 5-min should suffice for messenger send latency. Bump to 30 min if integration tests show race conditions.
