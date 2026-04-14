## Why

The backend has a single cleanup endpoint (`/task/clear-expired-cache`) that only clears expired tool cache entries. Meanwhile, messages, attachments, usage records, price alerts, and unaccepted sponsorships accumulate indefinitely. This wastes storage, keeps stale data around, and means multiple CRON jobs would be needed as cleanup concerns grow.

A unified `/task/cleanup` endpoint consolidates all data retention into one place, called by a single external CRON job.

## What Changes

- Replace `/task/clear-expired-cache` with `POST /task/cleanup` (same API key auth)
- Add a cleanup service that runs 5 phases in order:
  1. Delete attachments + messages older than 30 days (atomic — attachments first due to FK, no cascade)
  2. Clear expired cache (reuse existing `ToolsCacheCRUD.delete_expired()`)
  3. Delete usage records older than 30 days
  4. Delete price alerts not created/triggered in 360 days
  5. Delete unaccepted sponsorships older than 30 days
- Add 3 new config values: `cleanup_message_retention_days`, `cleanup_price_alert_staleness_days`, `cleanup_sponsorship_staleness_days`
- Add bulk-delete methods to CRUDs that don't already have them
- No notifications on any cleanup action
- No background processing — runs synchronously
- Users are never deleted (identity anchors with phone number verification)

## Capabilities

### New Capabilities

- `cleanup-service`: Unified data cleanup service with configurable retention periods, bulk deletes, and per-phase error isolation

### Modified Capabilities

## Impact

- `src/main.py` — replace `/task/clear-expired-cache` with `/task/cleanup`
- `src/util/config.py` — add 3 new config values
- `src/db/crud/chat_message.py` — add `delete_older_than()`
- `src/db/crud/chat_message_attachment.py` — add `delete_by_old_messages()`
- `src/db/crud/usage_record_repo.py` or new CRUD — add `delete_older_than()`
- `src/db/crud/price_alert.py` — add `delete_stale()`
- `src/db/crud/sponsorship.py` — add `delete_unaccepted_older_than()`
- New cleanup service file under `src/features/`
- New test file(s) for the cleanup service and new CRUD methods
- No DB migrations (no schema changes)
- No API contract changes beyond the endpoint rename
