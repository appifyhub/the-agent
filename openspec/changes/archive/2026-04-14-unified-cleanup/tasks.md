## 1. Add config values

- [x] 1.1 Add `cleanup_message_retention_days` (env `CLEANUP_MESSAGE_RETENTION_DAYS`, default 30) to `Config`
- [x] 1.2 Add `cleanup_price_alert_staleness_days` (env `CLEANUP_PRICE_ALERT_STALENESS_DAYS`, default 360) to `Config`
- [x] 1.3 Add `cleanup_sponsorship_staleness_days` (env `CLEANUP_SPONSORSHIP_STALENESS_DAYS`, default 30) to `Config`
- [x] 1.4 Update config test with new values

## 2. Add bulk-delete CRUD methods

- [x] 2.1 `ChatMessageAttachmentCRUD.delete_by_old_messages(cutoff: datetime) -> int` — delete attachments via subquery joining messages on `sent_at < cutoff`
- [x] 2.2 `ChatMessageCRUD.delete_older_than(cutoff: datetime) -> int` — bulk delete messages with `sent_at < cutoff`
- [x] 2.3 Add `delete_older_than(cutoff: datetime) -> int` to usage record repo — bulk delete usage records with `timestamp < cutoff`
- [x] 2.4 `PriceAlertCRUD.delete_stale(cutoff: datetime) -> int` — bulk delete alerts with `last_price_time < cutoff`
- [x] 2.5 `SponsorshipCRUD.delete_unaccepted_older_than(cutoff: datetime) -> int` — bulk delete where `accepted_at IS NULL AND sponsored_at < cutoff`
- [x] 2.6 Write tests for each new CRUD method

## 3. Create cleanup service

- [x] 3.1 Create `src/features/cleanup/cleanup_service.py` with `CleanupService` class
- [x] 3.2 Implement phase 1: attachments + messages (atomic block)
- [x] 3.3 Implement phase 2: expired cache (reuse `ToolsCacheCRUD.delete_expired()`)
- [x] 3.4 Implement phase 3: old usage records
- [x] 3.5 Implement phase 4: stale price alerts
- [x] 3.6 Implement phase 5: unaccepted sponsorships
- [x] 3.7 Return summary dict with per-phase counts
- [x] 3.8 Write tests for `CleanupService`

## 4. Wire up endpoint

- [x] 4.1 Replace `POST /task/clear-expired-cache` with `POST /task/cleanup` in `main.py`
- [x] 4.2 Endpoint calls `CleanupService`, returns summary JSON
- [x] 4.3 Verify API key auth works on the new endpoint

## 5. Verify

- [x] 5.1 Run full test suite — no regressions
- [x] 5.2 Run pre-commit linting
