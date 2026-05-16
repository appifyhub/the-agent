## 1. URL Resolution

- [x] 1.1 Add URL-to-virtual-attachment resolution function in `llm_tool_library.py`: HTTP HEAD for MIME type, extension parsing from URL path, fallback to `supported_files.py` lookup, build ephemeral `ChatMessageAttachment` with `url-<md5>` ID
- [x] 1.2 Add validation: reject URLs whose MIME type can't be determined or isn't in `KNOWN_FILE_FORMATS`

## 2. LLM Tool Changes

- [x] 2.1 Rename `process_attachments` → `process_media` in function name, `ALL_LLM_TOOLS` dict key, and docstring; add `urls: str | None` parameter; update docstring to describe both input sources
- [x] 2.2 Wire up `process_media` to resolve URLs into virtual attachments and merge with DB-resolved attachments before passing to processors; validate that at least one of `attachment_ids` or `urls` is provided

## 3. Processor Changes

- [x] 3.1 Modify `ChatAttachmentProcessor.__init__` to accept optional `pre_resolved_attachments` list; when provided, skip DB lookup and platform refresh for those; merge with any DB-resolved attachments
- [x] 3.2 Modify `ChatImageEditService.__init__` to accept optional `pre_resolved_attachments` list; when provided, skip `refresh_attachments_by_ids` for those; merge with any DB-resolved attachments
- [x] 3.3 Update DI factory methods (`chat_attachment_processor`, `chat_image_edit_service`) to pass through the new parameter

## 4. Tests

- [x] 4.1 Add tests for URL resolution: MIME from HEAD, MIME from extension fallback, unsupported type rejection, malformed URL handling
- [x] 4.2 Add tests for `process_media`: URL-only, attachment-only, mixed, neither (validation error)
- [x] 4.3 Add tests for `ChatAttachmentProcessor` with pre-resolved virtual attachments (verify no DB/SDK calls)
- [x] 4.4 Add tests for `ChatImageEditService` with pre-resolved virtual attachments (verify no DB/SDK calls)
