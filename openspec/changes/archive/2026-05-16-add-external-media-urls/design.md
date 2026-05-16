## Context

The LLM tool `process_attachments` currently only accepts attachment IDs — references to files stored in the DB after being received from Telegram/WhatsApp. The downstream processors (`ChatAttachmentProcessor`, `ChatImageEditService`) work with `ChatMessageAttachment` objects that carry a URL, MIME type, and extension. The attachment URLs contain bot tokens in their paths and must never be exposed to the LLM or logged.

External URLs provided by users are public and don't have this sensitivity. They need to enter the same processing pipeline without going through DB storage or platform SDK refresh.

## Goals / Non-Goals

**Goals:**
- Allow the LLM to process external URLs through the same media pipeline as chat attachments
- Support both `analyze` and `image-edit` operations for URL-sourced media
- Keep the change minimal — reuse existing processors, don't fork the pipeline
- Cache URL-based analysis results using URL hash as cache key

**Non-Goals:**
- No DB persistence of URL-sourced media
- No authentication/cookie support for fetching URLs behind login walls
- No new file format support — URLs must resolve to already-supported formats
- No changes to the attachment ingestion pipeline from platforms

## Decisions

### 1. Separate `urls` parameter instead of mixed-format input

Add `urls: str | None` as a new comma-separated parameter alongside existing `attachment_ids`. Do not merge them into a single field.

**Why:** LLMs (especially weaker ones) reliably fill separate named parameters but struggle with mixed-format strings where they'd need to prefix items correctly. Two params with clear names (`attachment_ids` for 📎 IDs, `urls` for http links) are unambiguous.

**Alternative considered:** Single `sources` param with prefix-based parsing (`📎abc,https://...`). Rejected for LLM reliability reasons.

### 2. Virtual attachments built at tool-library level

Resolve URLs into ephemeral `ChatMessageAttachment` objects in `llm_tool_library.py` before passing them to `ChatAttachmentProcessor` or `ChatImageEditService`. The processors receive the same type they already expect.

**Why:** Minimizes changes to downstream processors. They don't need to know whether an attachment came from DB or a URL — they just need an object with `last_url`, `mime_type`, and `extension`.

**Alternative considered:** Teaching each processor to accept raw URLs directly. Rejected because it duplicates resolution logic and touches more code.

### 3. MIME type detection via HTTP HEAD + URL extension fallback

For external URLs:
1. Parse extension from URL path (strip query params)
2. Send HTTP HEAD request to get `Content-Type` header
3. Use HEAD response if available, fall back to extension-based lookup from `supported_files.py`
4. Reject if MIME type can't be determined or isn't in `KNOWN_FILE_FORMATS`

**Why:** HEAD is cheap and gives the authoritative MIME type. Extension fallback handles servers that don't return Content-Type. Rejecting unknown types prevents the pipeline from silently failing on unsupported media.

### 4. Virtual attachment identity

Virtual attachments use a deterministic ID derived from a URL hash (e.g., `url-<md5>`). This gives:
- Stable cache keys for repeat analysis of the same URL
- Clear distinction from DB-backed attachment IDs (which are UUIDs)
- No collision with real attachment IDs

The `chat_id` field on virtual attachments will use the current invoker's chat ID.

### 5. Processor changes — accept pre-resolved attachments

Both `ChatAttachmentProcessor` and `ChatImageEditService` currently resolve attachments from IDs internally. They need a second entry path that accepts already-resolved `ChatMessageAttachment` objects (the virtual ones).

Approach: Add an optional `pre_resolved_attachments` parameter to both. When provided, these skip DB lookup and platform refresh. The existing `attachment_ids` path remains unchanged.

### 6. Rename `process_attachments` → `process_media`

The tool name and `ALL_LLM_TOOLS` key change. The docstring is updated to mention URLs. The `attachment_ids` parameter keeps its name and description (📎 IDs), and `urls` is added alongside it.

## Risks / Trade-offs

**Large file downloads** → No mitigation beyond HTTP timeouts. Users could paste URLs to very large files. The existing `requests.get()` in processors already loads content into memory. This is a pre-existing concern, not introduced by this change.

**URL liveness** → External URLs may go stale between processing calls. Unlike platform attachments (which get refreshed), there's no refresh mechanism. Acceptable for ephemeral, non-persisted media.

**HEAD request may be blocked** → Some servers block HEAD or return different Content-Type than the actual content. The extension fallback mitigates this. If both fail, the tool returns an error to the LLM.

**Cache key stability** → Same URL may serve different content over time. The cache TTL (13 weeks, matching existing attachment cache) is long. Acceptable trade-off — users can re-send the URL if content changed.
