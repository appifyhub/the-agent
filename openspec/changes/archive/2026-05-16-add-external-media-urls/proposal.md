## Why

The `process_attachments` LLM tool only accepts chat message attachment IDs (files sent via Telegram/WhatsApp). When a user pastes a URL to an image, audio file, or document in their message, the agent has no way to process that media — it can only fetch web page text via `fetch_web_content`. This means users can't say "analyze this image: https://example.com/photo.jpg" or "edit this photo: https://imgur.com/abc.png" and get the same media processing they'd get from sending the file directly.

## What Changes

- Rename `process_attachments` to `process_media` in the LLM tool library
- Add a new `urls` parameter (comma-separated list of external URLs) alongside the existing `attachment_ids` parameter
- Build URL-to-virtual-attachment resolution: HTTP HEAD for MIME type detection, extension parsing from URL path, construction of ephemeral `ChatMessageAttachment` objects
- Modify `ChatAttachmentProcessor` to accept pre-resolved attachments (skip DB lookup and platform refresh for virtual attachments)
- Modify `ChatImageEditService` to accept pre-resolved attachments (same skip logic)
- Use URL hash as cache key for URL-based inputs (same caching infra, no DB persistence)
- Both `analyze` and `image-edit` operations work with external URLs

## Capabilities

### New Capabilities

- `external-url-media-resolution`: Resolving external URLs into virtual `ChatMessageAttachment` objects with MIME type detection and extension parsing, usable by existing media processing pipelines

### Modified Capabilities

None.

## Impact

- `src/features/chat/llm_tools/llm_tool_library.py` — rename function, add `urls` param, URL resolution logic
- `src/features/chat/chat_attachment_processor.py` — accept pre-resolved attachments, skip DB/refresh for them
- `src/features/chat/chat_image_edit_service.py` — accept pre-resolved attachments, skip DB/refresh for them
- `src/di/di.py` — update factory signatures if needed
- Tests for all modified files
- No API changes, no DB migrations, no new dependencies
