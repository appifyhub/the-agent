## Why

Today the LLM can fetch a Twitter/X post as text via `fetch_web_content`, but cannot produce a shareable visual rendition of it. Users who want to share a tweet visually (forwarded into a chat, attached to a message) get a flat text excerpt instead of a card-styled image. We want a dedicated LLM tool that turns a social post URL into a styled, brand-themed card image, starting with Twitter/X and structured to extend to other platforms later.

## What Changes

- Add a new LLM-callable tool `render_social_post(url, aspect_ratio)` that produces a card image URL for a social post.
- Extend `TwitterStatusFetcher` with a structured-output mode (`as_structured()`) alongside the existing text mode (`as_text()`); cache the raw API response so both modes share the cache.
- Add `profile_image_url` to `user.fields`, `created_at` to `tweet.fields`, and `preview_image_url` to `media.fields` in the X API request.
- Bump the Twitter cache key prefix to `twitter-status-fetcher-structured` for the new structured cache (text path retains its existing key).
- Introduce an SVG-based card renderer that composes header (avatar, name, handle, datetime, agent logo), tweet text, photo grid (max 4, 2×2), and a low-opacity footer (X icon + shortened URL via `UrlShortener`).
- Add `resvg-py` as a new pip dependency for SVG → PNG rasterization (zero system deps, manylinux wheels).
- Ship Heebo Variable TTF (OFL) with the project for card text rendering.
- Theme color is selected from the dominant color of the profile photo, falling back to combined dominant of media photos, falling back to the agent's brand purple-blue.
- Card width is fixed per aspect ratio (1080 portrait/square, 1620 landscape); height is content-driven and grows past the target ratio when text or photos demand it.

## Capabilities

### New Capabilities
- `social-post-card-rendering`: LLM-callable rendering of social network posts (initially Twitter/X) into styled card images, plus the structured-data path that supplies the renderer.

### Modified Capabilities
<!-- None — no prior specs exist in openspec/specs/. -->

## Impact

- **New code**: `src/features/social_cards/` (renderer, theme extraction, SVG template, photo download); new LLM tool function in `src/features/chat/llm_tools/llm_tool_library.py`; structured-mode method on `src/features/web_browsing/twitter_status_fetcher.py`.
- **New asset**: Heebo Variable TTF under `src/assets/fonts/` (or equivalent location scouted at implementation time).
- **New deps**: `resvg-py` added to `Pipfile`.
- **API request changes**: extra fields on the X API call inside `TwitterStatusFetcher`; cache key prefix change for the structured cache (existing text cache untouched).
- **Reuses existing**: `tool_choice_resolver` for `ToolType.api_twitter`, `ImageUploader` (imgbb) for hosting the rendered PNG, `UrlShortener` for the footer link, `resolve_tweet_id` for URL parsing.
- **No breaking changes** to existing LLM tools or external APIs. The text path through `fetch_web_content` is unchanged.
