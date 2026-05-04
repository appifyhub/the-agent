## ADDED Requirements

### Requirement: Membership row identity

The system SHALL store at most one `ChatMembership` row per `(user_id, chat_id)` pair. The pair MUST be the primary key. The row carries the user's privacy preferences for this chat (`use_about_me`, `use_custom_prompt`) and a cached admin flag (`is_admin`).

#### Scenario: Unique membership per user-chat pair

- **WHEN** an attempt is made to insert a second `ChatMembership` row with the same `(user_id, chat_id)` pair
- **THEN** the insert MUST be rejected by the database (primary key violation)

#### Scenario: Membership carries the three required flags

- **WHEN** any `ChatMembership` row is read
- **THEN** the row MUST contain non-null boolean values for `is_admin`, `use_about_me`, and `use_custom_prompt`

### Requirement: Membership creation on first messaging interaction

The system SHALL upsert a `ChatMembership` row for the `(invoker, chat)` pair when an invoker first sends a message in a chat. The upsert MUST default `use_about_me=true`, `use_custom_prompt=true`, and `is_admin=false`. If a row already exists, the existing row MUST NOT be modified.

#### Scenario: New member sends first message

- **WHEN** a user sends a message in a chat where no `ChatMembership` row exists for `(user, chat)`
- **THEN** a new row is inserted with `use_about_me=true`, `use_custom_prompt=true`, `is_admin=false`

#### Scenario: Existing member sends another message

- **WHEN** a user with an existing `ChatMembership` row sends another message in the same chat
- **THEN** the existing row's preferences and `is_admin` flag MUST remain unchanged

### Requirement: Membership creation on settings access without prior interaction

The system SHALL create a `ChatMembership` row on-the-fly when an invoker fetches single-chat settings (`GET /user/{user_id}/chats/{chat_id}`) and no row exists. The on-the-fly defaults MUST be `use_about_me=false`, `use_custom_prompt=false`, `is_admin=false`. After insertion, the admin refresh procedure (see "Admin status refresh") MUST run and update `is_admin` if applicable.

#### Scenario: Settings detail fetch creates missing row with privacy-safe defaults

- **WHEN** a user fetches `GET /user/{user_id}/chats/{chat_id}` and no `ChatMembership` row exists
- **THEN** a new row is inserted with `use_about_me=false`, `use_custom_prompt=false`, `is_admin=false`
- **AND** the response reflects those values (after any subsequent admin refresh)

#### Scenario: Settings detail fetch leaves existing row unchanged

- **WHEN** a user fetches `GET /user/{user_id}/chats/{chat_id}` and a `ChatMembership` row already exists
- **THEN** the row's `use_about_me` and `use_custom_prompt` values MUST NOT be modified by the fetch

### Requirement: Admin status refresh

The system SHALL refresh the `is_admin` flag on `ChatMembership` rows lazily, only when an invoker fetches the chat list (`GET /user/{user_id}/chats`) or a single chat (`GET /user/{user_id}/chats/{chat_id}`). The refresh MUST NOT run on the messaging path. The refresh MAY upsert membership rows for chats where the invoker is an admin but no row exists yet.

#### Scenario: List fetch refreshes admin status across all rows

- **WHEN** a user fetches `GET /user/{user_id}/chats`
- **THEN** the system computes admin status for the invoker across the relevant chats
- **AND** updates `is_admin` on each existing membership row to match the computed value

#### Scenario: List fetch discovers admin chat with no prior row

- **WHEN** a user fetches `GET /user/{user_id}/chats` and is admin in a chat with no membership row yet
- **THEN** a new row is inserted for `(user, chat)` with `is_admin=true`, `use_about_me=true`, `use_custom_prompt=true`

#### Scenario: Messaging does not call platform admin API

- **WHEN** a user sends a message in a chat
- **THEN** the membership upsert path MUST NOT invoke the platform's "get chat administrators" API

### Requirement: Prompt resolution gate

The system SHALL inject the invoker's `about_me` into the prompt only when a `ChatMembership` row exists for `(invoker, chat)` AND `use_about_me=true` AND `invoker.about_me` is non-empty. The same rule applies to `custom_prompt` with `use_custom_prompt`. If the membership row does not exist, neither field MUST be injected.

#### Scenario: Membership opts in for about_me

- **WHEN** prompt composition runs for a chat where the invoker's membership has `use_about_me=true` and `invoker.about_me` is set
- **THEN** the about_me content is injected into the composed prompt

#### Scenario: Membership opts out of custom_prompt

- **WHEN** prompt composition runs for a chat where the invoker's membership has `use_custom_prompt=false`
- **THEN** the custom_prompt content MUST NOT be injected, regardless of whether `invoker.custom_prompt` is set

#### Scenario: No membership row → privacy-safe default

- **WHEN** prompt composition runs for a chat where no `ChatMembership` row exists for the invoker
- **THEN** neither `about_me` nor `custom_prompt` MUST be injected

### Requirement: Migration backfill from message history

The system SHALL backfill `chat_memberships` during the deployment Alembic migration. For each distinct `(author_id, chat_id)` pair in `chat_messages` where `author_id IS NOT NULL`, the migration MUST insert a `ChatMembership` row with `use_about_me=true`, `use_custom_prompt=true`. `is_admin` MUST be `true` only when the chat is private AND its `external_id` matches the user's `telegram_chat_id` or `whatsapp_user_id`; otherwise `false`. The migration MUST NOT call platform APIs.

#### Scenario: User who messaged in a group chat gets a membership row

- **WHEN** the migration runs and a `chat_messages` row exists for `(user, group_chat)`
- **THEN** a `ChatMembership` row is created with `use_about_me=true`, `use_custom_prompt=true`, `is_admin=false`

#### Scenario: Own private chat is detected as admin

- **WHEN** the migration runs for a user's private chat where `chat_configs.external_id` matches their `telegram_chat_id` or `whatsapp_user_id`
- **THEN** the created `ChatMembership` row has `is_admin=true`

#### Scenario: Migration is idempotent against pre-existing rows

- **WHEN** the migration is re-run (or runs concurrently with first-message hooks)
- **THEN** rows that already exist are not overwritten; the migration uses `ON CONFLICT DO NOTHING` semantics

### Requirement: Removal of chat-wide privacy toggles

The system SHALL drop the `use_about_me` and `use_custom_prompt` columns from `chat_configs` as part of the same migration. Domain schemas (`ChatConfig`, `ChatConfigSave`) MUST no longer expose these fields.

#### Scenario: chat_configs no longer carries the privacy columns

- **WHEN** any code reads from `chat_configs` after migration
- **THEN** the columns `use_about_me` and `use_custom_prompt` MUST NOT be present

#### Scenario: Down-migration restores columns with True defaults

- **WHEN** the down-migration runs
- **THEN** the columns are re-added with `NOT NULL DEFAULT true` and the table `chat_memberships` is dropped
- **AND** the migration documentation explicitly notes that per-user preference granularity is lost on rollback
