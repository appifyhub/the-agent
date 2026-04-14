## Context

The backend currently has one cleanup endpoint (`POST /task/clear-expired-cache`) that calls `ToolsCacheCRUD.delete_expired()`. Other data — messages, attachments, usage records, price alerts, unaccepted sponsorships — has no expiry. All CRUD classes use individual `delete()` methods; only `ToolsCacheCRUD` has a bulk `delete_expired()`.

The `chat_message_attachments` table has an FK to `chat_messages(chat_id, message_id)` with **no ON DELETE CASCADE**, meaning attachments must be deleted before their parent messages.

Users are never deleted because their profiles carry phone number verification ("real human" proof) from Telegram/WhatsApp onboarding.

## Goals / Non-Goals

**Goals:**

- Single `POST /task/cleanup` endpoint replaces `/task/clear-expired-cache`
- Configurable retention periods via environment variables
- Bulk deletes for performance (SQLAlchemy `query.filter(...).delete()`)
- Per-phase error isolation — one phase failing doesn't block others
- Attachment-then-message ordering to respect FK constraints

**Non-Goals:**

- User deletion (identity anchors)
- Notifications on cleanup (decided against — too noisy)
- Background/async processing (start synchronous, revisit if needed)
- Purchase record cleanup (financial audit trail, kept forever)
- Chat config cleanup (tied to users, stay forever)

## Decisions

### Unified cleanup service with ordered phases

A single `CleanupService` class runs 5 phases in a fixed order. Phases 1a/1b (attachments + messages) are wrapped in one try/except block because they have an FK dependency. Phases 2-5 are each independently wrapped.

**Why ordered phases instead of parallel**: Simplicity. No threading complexity, no partial-failure coordination. The total volume per CRON run should be small if run regularly. If performance becomes an issue, backgrounding can be added later without changing the service interface.

### Retention periods shared between messages and usage records

Both messages and usage records use `cleanup_message_retention_days` (default 30). This keeps the config surface small. Usage records aren't financial records (purchase_records are), and 30 days matches message retention.

**Alternative considered**: Separate `cleanup_usage_retention_days`. Rejected because usage records are internal activity logs, not regulated data. GDPR mandates data minimization. Purchase records (kept forever) are the financial audit trail.

### Price alert staleness at 360 days

`last_price_time` is updated only on alert creation and when the threshold is crossed (trigger). It is NOT updated on routine CRON price checks. This makes it a reliable "last relevant activity" indicator. 360 days gives wide-threshold alerts (e.g., "notify me if BTC drops 50%") a full year to trigger before cleanup.

### Bulk delete via SQLAlchemy filter + delete

New CRUD methods use `query.filter(...).delete()` returning the count of deleted rows. This matches the existing pattern in `ToolsCacheCRUD.delete_expired()`. No need to load rows into memory.

For the attachment cleanup, we use a subquery: delete attachments whose `(chat_id, message_id)` matches messages with `sent_at` older than the cutoff. This avoids a two-step load-then-delete.

### No DB migration needed

All cleanup is row deletion based on existing date columns. No new columns, no schema changes. The new config values are environment variables with defaults.

## Risks / Trade-offs

- **Bulk delete lock contention**: Large deletes can hold table-level locks on Postgres. → Mitigation: if run regularly (daily), each batch is small. If backlog is large on first run, may cause brief lock contention. Acceptable for a CRON-triggered maintenance task.
- **Attachment subquery complexity**: Joining attachments to messages for bulk delete is more complex than simple date filtering. → Mitigation: straightforward subquery on `sent_at`; Postgres handles this efficiently with the existing index.
- **Usage records at 30 days**: Users lose visibility into spending after 30 days. → Mitigation: the backoffice usage stats endpoint aggregates on-the-fly; users wanting longer history can export or the retention can be increased via config.
