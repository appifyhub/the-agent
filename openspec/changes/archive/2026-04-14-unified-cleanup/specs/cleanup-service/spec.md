## ADDED Requirements

### Requirement: Unified cleanup endpoint
The system SHALL expose `POST /task/cleanup` authenticated via API key. It SHALL replace the existing `POST /task/clear-expired-cache` endpoint. The response SHALL be a JSON object with counts of deleted items per phase.

#### Scenario: Successful cleanup run
- **WHEN** `POST /task/cleanup` is called with a valid API key
- **THEN** the system SHALL execute all cleanup phases and return a JSON response with keys: `messages_deleted`, `attachments_deleted`, `cache_entries_cleared`, `usage_records_deleted`, `price_alerts_deleted`, `sponsorships_deleted`

#### Scenario: Unauthorized cleanup attempt
- **WHEN** `POST /task/cleanup` is called without a valid API key
- **THEN** the system SHALL return HTTP 401

### Requirement: Message and attachment cleanup (Phase 1)
The system SHALL delete chat message attachments and then chat messages where `sent_at` is older than `cleanup_message_retention_days` (default 30). Attachments SHALL be deleted before messages to satisfy FK constraints. Both deletions SHALL be wrapped in a single error handling block — if attachment deletion fails, message deletion SHALL be skipped.

#### Scenario: Old messages and their attachments are deleted
- **WHEN** cleanup runs and messages exist with `sent_at` older than 30 days
- **THEN** attachments belonging to those messages SHALL be deleted first, then the messages themselves

#### Scenario: Attachment deletion fails
- **WHEN** attachment deletion raises an exception
- **THEN** message deletion SHALL be skipped, remaining phases SHALL still execute

### Requirement: Expired cache cleanup (Phase 2)
The system SHALL delete tool cache entries where `expires_at < now()`. This SHALL reuse the existing `ToolsCacheCRUD.delete_expired()` method.

#### Scenario: Expired cache cleared
- **WHEN** cleanup runs and expired cache entries exist
- **THEN** those entries SHALL be deleted

### Requirement: Usage record cleanup (Phase 3)
The system SHALL delete usage records where `timestamp` is older than `cleanup_message_retention_days` (default 30). This shares the message retention config value.

#### Scenario: Old usage records are deleted
- **WHEN** cleanup runs and usage records exist with `timestamp` older than 30 days
- **THEN** those records SHALL be deleted

### Requirement: Price alert cleanup (Phase 4)
The system SHALL delete price alerts where `last_price_time` is older than `cleanup_price_alert_staleness_days` (default 360).

#### Scenario: Stale price alerts are deleted
- **WHEN** cleanup runs and price alerts have `last_price_time` older than 360 days
- **THEN** those alerts SHALL be deleted

### Requirement: Unaccepted sponsorship cleanup (Phase 5)
The system SHALL delete sponsorships where `accepted_at IS NULL` and `sponsored_at` is older than `cleanup_sponsorship_staleness_days` (default 30).

#### Scenario: Stale unaccepted sponsorships are deleted
- **WHEN** cleanup runs and sponsorships exist where `accepted_at` is NULL and `sponsored_at` is older than 30 days
- **THEN** those sponsorships SHALL be deleted

### Requirement: Per-phase error isolation
Phases 2, 3, 4, and 5 SHALL each be independently wrapped in error handling. A failure in any one phase SHALL NOT prevent execution of subsequent phases. Phase 1 (attachments + messages) is a single atomic block.

#### Scenario: One independent phase fails
- **WHEN** phase 3 (usage records) raises an exception
- **THEN** phases 4 and 5 SHALL still execute, and the response SHALL include 0 for the failed phase's count

### Requirement: Configurable retention periods
The system SHALL support 3 new environment-variable-backed config values with the following defaults:
- `CLEANUP_MESSAGE_RETENTION_DAYS` = 30 (used for messages, attachments, and usage records)
- `CLEANUP_PRICE_ALERT_STALENESS_DAYS` = 360
- `CLEANUP_SPONSORSHIP_STALENESS_DAYS` = 30

#### Scenario: Custom retention via environment variable
- **WHEN** `CLEANUP_MESSAGE_RETENTION_DAYS` is set to 60
- **THEN** messages, attachments, and usage records older than 60 days SHALL be deleted

### Requirement: Bulk deletes
All cleanup phases SHALL use bulk `DELETE WHERE` queries (not row-by-row loading and deletion). This follows the existing pattern in `ToolsCacheCRUD.delete_expired()`.

#### Scenario: Bulk message deletion
- **WHEN** 1000 messages are older than the retention period
- **THEN** they SHALL be deleted in a single SQL statement, not 1000 individual deletes
