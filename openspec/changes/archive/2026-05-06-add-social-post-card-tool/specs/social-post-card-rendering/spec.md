## ADDED Requirements

### Requirement: LLM Tool for Social Post Card Rendering
The system SHALL expose an LLM-callable tool named `render_social_post` that accepts a social network post URL and an optional aspect ratio, and returns a hosted image URL of a rendered card. The tool SHALL be registered in the LLM tool library and bound to the chat model alongside the existing tools.

#### Scenario: Successful render of a Twitter/X post
- **WHEN** the LLM invokes `render_social_post` with a valid Twitter/X URL and `aspect_ratio="2:3"`
- **THEN** the tool fetches the tweet's structured data, renders a card image with header, tweet text, and any photos, uploads the resulting PNG, and returns a JSON success response containing the hosted image URL

#### Scenario: Default aspect ratio
- **WHEN** the LLM invokes `render_social_post` with only a `url` argument and no `aspect_ratio`
- **THEN** the tool uses portrait orientation (`"2:3"`) as the default

#### Scenario: Invalid social network URL
- **WHEN** the LLM invokes `render_social_post` with a URL that does not resolve to a supported social post (e.g., `https://example.com/foo`)
- **THEN** the tool returns a JSON error response and does NOT fall back to rendering the URL as plain text

#### Scenario: Render or upload failure
- **WHEN** any internal step (API call, photo download, SVG render, image upload) raises an error
- **THEN** the tool returns a JSON error response with a descriptive message and does NOT fall back to text content

### Requirement: Aspect Ratio Support
The tool SHALL support the aspect ratio values `"1:1"`, `"2:3"`, and `"3:2"`. The aspect ratio SHALL determine the card's fixed pixel width and minimum height, and SHALL drive the photo grid layout decision. The actual rendered card height SHALL grow beyond the target height when content (tweet text length or photo count) requires it.

#### Scenario: Portrait card width and minimum height
- **WHEN** rendering with `aspect_ratio="2:3"`
- **THEN** the card width is fixed at 1080 pixels and the minimum height is 1620 pixels

#### Scenario: Landscape card width and minimum height
- **WHEN** rendering with `aspect_ratio="3:2"`
- **THEN** the card width is fixed at 1620 pixels and the minimum height is 1080 pixels

#### Scenario: Square card dimensions
- **WHEN** rendering with `aspect_ratio="1:1"`
- **THEN** the card width and minimum height are both 1080 pixels

#### Scenario: Content exceeds target height
- **WHEN** the rendered tweet text and photos require more vertical space than the minimum height for the chosen aspect ratio
- **THEN** the card grows vertically to fit the content; the width remains at the aspect ratio's fixed value

### Requirement: Photo Grid Layout
The card SHALL render up to 4 photos in a grid whose column count depends on card orientation and aggregate photo orientation. Outer corners of the photo block SHALL be rounded; inner edges between adjacent photos SHALL remain square.

#### Scenario: Portrait card forces single column
- **WHEN** `aspect_ratio="2:3"` and the tweet contains 2 or more photos
- **THEN** photos are stacked in a single column

#### Scenario: Landscape or square card with majority portrait photos
- **WHEN** `aspect_ratio` is `"1:1"` or `"3:2"` and fewer than 50% of the tweet's photos are landscape
- **THEN** photos are arranged in a 2-column grid

#### Scenario: Landscape or square card with majority landscape photos
- **WHEN** `aspect_ratio` is `"1:1"` or `"3:2"` and 50% or more of the tweet's photos are landscape
- **THEN** photos are stacked in a single column

#### Scenario: Selective corner rounding
- **WHEN** rendering a multi-row photo grid
- **THEN** only the top-left and top-right corners of the first row, and the bottom-left and bottom-right corners of the last row, are rounded; all interior corners remain square

### Requirement: Card Header Layout
The card SHALL display a fixed-height header containing, on the left, a circular profile photo followed by the post author's name with handle and a formatted datetime, and on the right, the agent's service logo.

#### Scenario: Profile photo retrieval
- **WHEN** the tweet's user data includes a `profile_image_url`
- **THEN** the renderer fetches the `_bigger` (73×73) variant by transforming the URL suffix and renders it cropped to a circle

#### Scenario: Name and handle rendering
- **WHEN** the user has a non-empty display name
- **THEN** the header renders `<DisplayName> (@<handle>)` on the first text row

#### Scenario: Empty display name
- **WHEN** the user has no display name
- **THEN** the header renders `@<handle>` only on the first text row

#### Scenario: Datetime format
- **WHEN** rendering the header with the tweet's `created_at` timestamp
- **THEN** the datetime is formatted as `YYYY-MM-DD · UTC h:mm AM/PM` (e.g., `2026-05-04 · UTC 4:13 PM`)

#### Scenario: Service logo placement
- **WHEN** rendering the header
- **THEN** the agent service logo (an SVG) is placed at fixed size on the right side of the header row

### Requirement: Card Body and Footer
The card body SHALL render the tweet text in a single column with automatic word wrapping, followed by the photo grid (if any). A footer row at the bottom of the card SHALL render the X icon followed by a shortened version of the original tweet URL at low opacity.

#### Scenario: Tweet text wrapping
- **WHEN** rendering tweet text that exceeds one line at the card's text width
- **THEN** text wraps at word boundaries and the card body grows vertically to accommodate all lines

#### Scenario: Footer URL shortening
- **WHEN** rendering the footer
- **THEN** the original tweet URL is shortened via `UrlShortener` and the resulting short URL is displayed next to the X icon

#### Scenario: Footer styling
- **WHEN** rendering the footer
- **THEN** the X icon and short URL are rendered at reduced opacity to remain subtle relative to the tweet content

### Requirement: Theme Color Selection
The card SHALL apply a linear-gradient background derived from a primary color chosen by a three-tier fallback. The gradient's second color SHALL be derived from the primary by lightness and hue shifts. Foreground text color SHALL be chosen for contrast against the primary color.

#### Scenario: Primary color from profile photo
- **WHEN** the tweet's profile photo can be downloaded and analyzed
- **THEN** the primary color is the dominant color extracted from the profile photo

#### Scenario: Primary color from media photos
- **WHEN** no profile photo is available or its dominant color cannot be determined, and the tweet has media photos
- **THEN** the primary color is the dominant color across all media photos combined

#### Scenario: Default brand color fallback
- **WHEN** neither the profile photo nor media photos yield a usable dominant color
- **THEN** the primary color is the agent's brand purple-blue (sourced from `agent.appifyhub.com`)

#### Scenario: Gradient second-color derivation
- **WHEN** the primary color is selected
- **THEN** the gradient's second stop is the primary color shifted by approximately 10% in lightness (away from neutral) and approximately 10° in hue toward red or blue

#### Scenario: Foreground text contrast
- **WHEN** rendering text on the themed background
- **THEN** the text color is black or white, chosen to maximize contrast against the primary color

### Requirement: Image Output and Hosting
The renderer SHALL produce a PNG image, upload it via the existing `ImageUploader` (imgbb), and return the hosted URL to the LLM. No persistent storage of the rendered card is required beyond the upload provider's expiration.

#### Scenario: PNG output and upload
- **WHEN** the SVG card is rasterized
- **THEN** the renderer produces PNG bytes, passes them to `ImageUploader`, and returns the resulting hosted URL string in the LLM tool's success response

### Requirement: Structured Mode in TwitterStatusFetcher
`TwitterStatusFetcher` SHALL provide both a text-output mode (existing behavior) and a structured-output mode that returns the raw tweet data as a typed object without invoking computer-vision photo analysis. Both modes SHALL share the underlying X API call but use distinct caches.

#### Scenario: Structured mode returns raw data
- **WHEN** `as_structured()` is called
- **THEN** the fetcher returns a typed object containing the user (name, handle, bio, profile image URL), the tweet (text, language, created_at), and a list of media items (URLs and types) without running computer vision over photos

#### Scenario: Text mode preserves existing behavior
- **WHEN** `as_text()` is called
- **THEN** the fetcher returns a formatted text string equivalent to the current `execute()` output, including computer-vision descriptions of photos

#### Scenario: Structured mode cache key
- **WHEN** the structured mode caches its result
- **THEN** the cache key uses prefix `twitter-status-fetcher-structured`, distinct from the text mode's existing prefix

#### Scenario: Cache reuse across modes
- **WHEN** the same tweet is requested in both modes within the cache TTL
- **THEN** each mode hits its own cache on the second call; the X API is called at most once per mode within the TTL window

### Requirement: Extended X API Request Fields
The X API request issued by `TwitterStatusFetcher` SHALL include `profile_image_url` in `user.fields`, `created_at` in `tweet.fields`, and `preview_image_url` in `media.fields` to support the card-rendering data needs.

#### Scenario: Request includes new fields
- **WHEN** `TwitterStatusFetcher` issues a request to the X API
- **THEN** the query parameters include `user.fields=name,username,description,profile_image_url`, `tweet.fields=lang,text,created_at`, and `media.fields=url,type,preview_image_url`

### Requirement: GIF and Video Handling
The renderer SHALL treat animated GIFs and videos as still images by using the X-supplied `preview_image_url` poster frame. No play-button overlay or motion indicator SHALL be added.

#### Scenario: Animated GIF in tweet
- **WHEN** the tweet contains a media item of type `animated_gif`
- **THEN** the renderer uses the item's `preview_image_url` as the rendered photo with no overlay

#### Scenario: Video in tweet
- **WHEN** the tweet contains a media item of type `video`
- **THEN** the renderer uses the item's `preview_image_url` as the rendered photo with no overlay
