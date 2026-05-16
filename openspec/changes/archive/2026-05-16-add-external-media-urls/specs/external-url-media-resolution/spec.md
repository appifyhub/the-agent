## ADDED Requirements

### Requirement: LLM tool accepts external URLs for media processing

The `process_media` tool SHALL accept an optional `urls` parameter containing a comma-separated list of external URLs. At least one of `attachment_ids` or `urls` MUST be provided. Both MAY be provided simultaneously, in which case results from both sources are merged.

#### Scenario: URL-only media analysis
- **WHEN** the LLM calls `process_media` with `urls: "https://example.com/photo.jpg"` and `operation: "analyze"`
- **THEN** the system fetches the URL, detects its MIME type, routes it through the image analysis pipeline, and returns a text description

#### Scenario: URL-only image editing
- **WHEN** the LLM calls `process_media` with `urls: "https://example.com/photo.jpg"` and `operation: "image-edit"`
- **THEN** the system fetches the URL, treats it as a reference image, and generates an edited image delivered to the user

#### Scenario: Mixed attachments and URLs
- **WHEN** the LLM calls `process_media` with both `attachment_ids: "📎abc-123"` and `urls: "https://example.com/photo.jpg"` and `operation: "analyze"`
- **THEN** the system processes both sources and returns combined results for all inputs

#### Scenario: Neither parameter provided
- **WHEN** the LLM calls `process_media` with both `attachment_ids` and `urls` empty or missing
- **THEN** the system returns a validation error indicating at least one source is required

### Requirement: External URLs are resolved into virtual attachments

The system SHALL resolve each external URL into an ephemeral `ChatMessageAttachment` object with a deterministic ID (`url-<md5_of_url>`), the URL as `last_url`, and detected MIME type and extension. These virtual attachments SHALL NOT be persisted to the database.

#### Scenario: MIME type detected from HTTP HEAD
- **WHEN** an external URL is resolved and the server responds to HTTP HEAD with a valid `Content-Type` header matching a known format
- **THEN** the virtual attachment uses that MIME type and the corresponding extension

#### Scenario: MIME type detected from URL extension
- **WHEN** an external URL is resolved and the HTTP HEAD either fails or returns no usable `Content-Type`, but the URL path contains a recognized file extension
- **THEN** the virtual attachment uses the MIME type mapped from that extension via `supported_files.py`

#### Scenario: MIME type cannot be determined
- **WHEN** an external URL is resolved and neither HTTP HEAD nor URL extension yields a known MIME type
- **THEN** the system returns an error for that URL indicating the media type is unsupported

### Requirement: Virtual attachments skip DB lookup and platform refresh

When `ChatAttachmentProcessor` or `ChatImageEditService` receive pre-resolved virtual attachments, they SHALL skip the database lookup and platform SDK refresh steps. The processing pipeline (image analysis, audio transcription, document search, image editing) SHALL work identically regardless of attachment source.

#### Scenario: Analyze path with virtual attachment
- **WHEN** `ChatAttachmentProcessor` receives a virtual attachment with a valid image URL and MIME type
- **THEN** it processes the image through computer vision analysis without any DB or platform SDK calls

#### Scenario: Image-edit path with virtual attachment
- **WHEN** `ChatImageEditService` receives a virtual attachment with a valid image URL
- **THEN** it passes the URL to `ImageEditor` without calling `refresh_attachments_by_ids`

### Requirement: URL-based results are cached using URL hash

The system SHALL cache analysis results for URL-based inputs using the URL's MD5 hash as the cache key (same prefix and TTL as attachment-based caching). Repeat analysis of the same URL with the same context within the cache TTL SHALL return cached results.

#### Scenario: Cache hit on repeated URL analysis
- **WHEN** the same URL is analyzed twice with the same context within the cache TTL
- **THEN** the second call returns cached results without re-fetching or re-analyzing

#### Scenario: Cache miss on different context
- **WHEN** the same URL is analyzed with a different context string
- **THEN** the system re-fetches and re-analyzes, producing a new cache entry
