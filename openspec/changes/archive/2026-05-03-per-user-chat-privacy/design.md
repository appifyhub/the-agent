## Context

The agent-backend exposes `about_me` and `custom_prompt` as personalization signals on every user. Whether they get injected into a chat's prompt is currently controlled by two booleans on `chat_configs` (`use_about_me`, `use_custom_prompt`). Those flags are global to the chat — a chat admin can flip them and the change applies to **everyone** in the chat, including users whose data is being injected without their consent. This is a privacy violation pattern.

There's no `user ↔ chat` membership table today. Membership is inferred indirectly:
- For private chats: matching `external_id` against the user's platform IDs (`telegram_chat_id`, `whatsapp_user_id`).
- For group chats: live calls to `Telegram.getChatAdministrators()` to detect admin status.
- For non-admin participation: derived implicitly from `chat_messages.author_id` (no membership row).

Settings UI today is admin-gated end-to-end:
- `GET /user/{id}/chats` returns only chats the user administers.
- `GET /settings/chat/{chat_id}` and `PATCH /settings/chat/{chat_id}` require admin.
- A non-admin member cannot see, list, or change anything — including their own privacy preferences.

Frontend (`../agent-web/src/pages/ChatSettingsPage.tsx`) treats `use_about_me` / `use_custom_prompt` as toggles on the chat settings, alongside `language`, `reply_chance_percent`, etc.

## Goals / Non-Goals

**Goals:**
- Make `use_about_me` / `use_custom_prompt` per-user-per-chat, not per-chat.
- Let any chat member access their own settings page; only admins can change chat-wide settings.
- Eliminate the platform API call (`getChatAdministrators`) from the messaging hot path.
- Keep the API contract simple for the web app: one fetch endpoint, one save endpoint, one nested payload that round-trips cleanly.
- Provide a clean migration: existing users keep working, with sensible defaults derived from message history.

**Non-Goals:**
- Changing how `about_me` / `custom_prompt` are *stored* on the user (still on `simulants`, encrypted as before).
- Changing prompt composition for any path other than per-user privacy gating (no rewrite of `prompt_resolvers.py` beyond the gate check).
- Real-time admin status refresh — admin flag is allowed to lag until the user opens settings.
- Adding membership rows for chats the user has never participated in or administered (no eager backfill from platform APIs).
- Sponsored/support-staff editing another user's per-chat preferences (out of scope; preferences are always invoker's own).

## Decisions

### 1. New table + Repository: `chat_memberships`

```
chat_memberships
  user_id            UUID  FK → simulants.id      NOT NULL
  chat_id            UUID  FK → chat_configs.id   NOT NULL
  is_admin           BOOL  NOT NULL  DEFAULT false
  use_about_me       BOOL  NOT NULL  DEFAULT true
  use_custom_prompt  BOOL  NOT NULL  DEFAULT true
  PRIMARY KEY (user_id, chat_id)
  INDEX (user_id)
  INDEX (chat_id)
```

**File structure** (follows the `purchase_record_repo` / `usage_record_repo` pattern):
- `db/model/chat_membership.py` — SQLAlchemy `ChatMembershipDB` model (table definition only).
- `features/chat/membership/chat_membership.py` — `@dataclass(kw_only=True) ChatMembership` domain object.
- `features/chat/membership/chat_membership_mapper.py` — `db()` and `domain()` converter functions between DB model and domain object.
- `features/chat/membership/chat_membership_repo.py` — `ChatMembershipRepository`; all methods accept and return `ChatMembership` domain objects, never `ChatMembershipDB`.

No `db/schema/` Pydantic schema and no `db/crud/` class are created — the project is migrating to the Repository pattern for new persistence units.

**Rationale**: composite PK is natural — one row per user per chat. Indexes on each column individually support both "all chats for a user" (settings list) and "this user's preference for this chat" (prompt resolution) lookups.

**Why DB default `True` even though API virtual default is `False`**: the DB default matches the *historical* behavior (the legacy `chat_configs` columns defaulted to `True`), so migration backfill and first-message creation both produce `True` rows. The `False` default kicks in only when an API caller asks about a chat with no membership row at all (a rare, transient state — see Decision #4).

**Alternatives considered:**
- *Reuse `chat_messages` to derive membership* (no new table): rejected because we need to store `is_admin` and the two preference booleans somewhere stable, and we want the membership concept to be first-class.
- *Separate tables for membership and preferences*: rejected as over-engineering for two booleans + one flag.
- *CRUD pattern* (`db/schema/` + `db/crud/`): rejected — the project uses the Repository pattern for new persistence units; CRUD is legacy.

### 2. Prompt resolver: lookup with null check, default `False`

```python
# prompt_resolvers.py (invoker_membership: ChatMembership | None passed in by caller)
if invoker_membership and invoker_membership.use_about_me and invoker.about_me:
    ...inject about_me...
if invoker_membership and invoker_membership.use_custom_prompt and invoker.custom_prompt:
    ...inject custom_prompt...
```

The caller (`chat_agent.py`) fetches the membership via `di.chat_membership_repo.get(invoker.id, target_chat.chat_id)` and passes it as a parameter. `ChatMembershipRepository.get()` returns `ChatMembership | None` (domain object). No exception, no fabricated row — the prompt path is hot, we don't write on read.

**Why default `False` here, not `True`**: prompt resolution is a privacy boundary. If we don't have an explicit, persisted yes from this user, we don't inject their personal data. This also stays consistent with the API: no row → both flags appear as `false` in responses.

### 3. Membership creation lifecycle

Three creation paths, all converging on the same upsert:

| Path | When | Defaults |
|------|------|----------|
| Migration | Alembic backfill | `use_about_me=True`, `use_custom_prompt=True`; `is_admin=True` if private own-chat (by `external_id` match), else `False` |
| First-message hook | `telegram_data_resolver.py`, `whatsapp_data_resolver.py` after persisting the user + chat config | `use_about_me=True`, `use_custom_prompt=True`, `is_admin=False` |
| API on-the-fly | `GET /user/{u}/chats/{c}` finds no row | `use_about_me=False`, `use_custom_prompt=False`, `is_admin=False` (admin refresh runs immediately after) |

The API on-the-fly path uses `False` defaults intentionally — it covers the edge case where someone hits the settings UI for a chat they've never messaged in (e.g., a brand-new admin who's never spoken). They should opt in explicitly, not silently inherit the `True` default.

The first-message-hook path uses `True` defaults to match what existing users experienced before this change. Anyone who's ever messaged the bot before this change saw `about_me`/`custom_prompt` injected by default (chat admins had to opt-out); preserving `True` keeps the upgrade transparent for regular users.

**Idempotency**: all three paths use upsert semantics. Migration → existing rows untouched. First-message → only inserts if no row exists (don't reset preferences on every message). API on-the-fly → only inserts if no row exists (so a returning member keeps their saved preferences).

### 4. Lazy `is_admin` refresh

`is_admin` is computed expensively (Telegram `getChatAdministrators` is a network call). We don't want this on the messaging path. Refresh windows:

- `GET /user/{u}/chats` (list): for the invoker only, run the existing `get_authorized_chats` admin check across all their chats; upsert membership rows for any admin chats not yet in the table; flip `is_admin` on existing rows when the platform answer changes.
- `GET /user/{u}/chats/{c}` (detail): for this single chat, run the same admin check and update the row.

This makes the settings list (and by extension the dropdown the web app loads on every page) the natural refresh point. It's once-per-page-load cost on a non-real-time path. The flag is allowed to be stale between settings visits.

**Alternatives considered:**
- *Refresh on every message*: rejected — adds a Telegram API call to every group message, a real performance regression.
- *Background job to refresh periodically*: rejected — extra infra (cron/queue) for a benefit barely above lazy refresh.
- *Don't store, always compute live*: rejected — the membership row already needs to exist for preferences, and the live admin check is already what we'd do; storing the answer just makes subsequent reads (e.g., the prompt path's authorization checks, if ever needed) cheap.

### 5. REST endpoint shape

```
GET   /user/{user_id}/chats             → array of full ChatSettingsResponse
GET   /user/{user_id}/chats/{chat_id}   → single ChatSettingsResponse
PATCH /user/{user_id}/chats/{chat_id}   → save with nested payload

Retired:
  PATCH /settings/chat/{chat_id}
  GET   /settings/chat/{chat_id}  (the chat branch of /settings/{settings_type}/{resource_id})
```

`GET /settings/{settings_type}/{resource_id}` keeps the `user` branch and drops the `chat` one. The `SettingsType` enum survives as `user`-only or gets simplified to a fixed path.

**Response/payload shape (both directions):**

```json
{
  "chat_config": {
    "chat_id": "...",
    "title": "...",
    "platform": "telegram",
    "language_iso_code": "en",
    "language_name": "English",
    "is_private": false,
    "is_own": false,
    "is_admin": true,
    "reply_chance_percent": 100,
    "release_notifications": "major",
    "media_mode": "photo"
  },
  "user_chat_config": {
    "use_about_me": true,
    "use_custom_prompt": false
  }
}
```

PATCH payload uses the same nested shape, both keys optional:
- `user_chat_config` is always allowed (any member).
- `chat_config` is only honored when invoker has `is_admin=True` for this chat — otherwise `AuthorizationError` if any chat-config field is included.

**Why one save endpoint, not two**: the frontend already saves all settings in one click; two endpoints would force it to make sequential calls and reconcile partial-failure states. One endpoint with payload-level authorization keeps the UX atomic and the API surface smaller.

**Why retire `/settings/chat/{chat_id}` entirely**: chat settings are now genuinely user-scoped (the `user_chat_config` portion is per-invoker). A URL without the user dimension lies about that. Worth the breaking change.

### 6. Authorization split

`authorization_service.py` gets two member-aware methods next to the existing admin one:

- `validate_chat_member(user, chat)` — returns the `ChatMembership` row (creating it on-the-fly if missing, with `False` defaults). Used by `GET /user/{u}/chats/{c}` and the user_chat_config branch of PATCH.
- `validate_chat_admin(user, chat)` — wraps existing `authorize_for_chat` (which calls `get_authorized_chats`). Used by the chat_config branch of PATCH. Side effect: updates `is_admin` on the membership row.
- `get_authorized_chats(user)` — kept as the helper that drives the lazy admin refresh in the list endpoint.

`authorize_for_user` keeps its current behavior (verifies invoker can act on the target user's resources via JWT — needed for the `{user_id}` URL segment).

### 7. Migration

One Alembic migration, no Python pre/post-deploy scripts. Steps:

1. `CREATE TABLE chat_memberships` with the schema above.
2. Backfill from `chat_messages`:
   ```sql
   INSERT INTO chat_memberships (user_id, chat_id, is_admin, use_about_me, use_custom_prompt)
   SELECT DISTINCT
     m.author_id,
     m.chat_id,
     -- is_admin = own private chat (where external_id matches user's platform handle)
     CASE
       WHEN c.is_private AND c.external_id IS NOT NULL AND (
         c.external_id = u.telegram_chat_id OR c.external_id = u.whatsapp_user_id
       ) THEN true
       ELSE false
     END,
     true,  -- use_about_me default
     true   -- use_custom_prompt default
   FROM chat_messages m
   JOIN simulants u   ON u.id = m.author_id
   JOIN chat_configs c ON c.chat_id = m.chat_id
   WHERE m.author_id IS NOT NULL
   ON CONFLICT (user_id, chat_id) DO NOTHING;
   ```
3. `ALTER TABLE chat_configs DROP COLUMN use_about_me, DROP COLUMN use_custom_prompt`.

Down-migration restores the columns with `True` defaults but does **not** attempt to recompute their values from membership rows (the original semantics are gone — there's no single answer). Documented in the migration file.

**Rationale for SQL backfill rather than calling code**: SQL is faster, atomic with the DDL, and doesn't depend on application boot order during deploy. We don't need Telegram API calls during migration — admin status is allowed to lag (Decision #4).

### 8. CHANGELOG.md in `../agent-web`

The frontend will need to update its API client and ChatSettingsPage. We write a `CHANGELOG.md` in `../agent-web` documenting:
- Endpoints added / removed / shape-changed.
- New nested response/payload structure.
- The privacy semantics shift (so the web team understands *why*, not just what).

This is a one-time handoff document — it gets created once during this change, not maintained in lockstep with future changes.

## Risks / Trade-offs

- **Breaking API change** → web app must deploy in lockstep with the backend. Mitigation: ship the CHANGELOG.md with the proposal so the web team can prep their PR; coordinate the cutover; release notes will mention the privacy migration.
- **Stale `is_admin`** between settings page visits → user appears as admin/non-admin based on last refresh, not live state. Mitigation: refresh runs on every list/detail fetch (cheap from the user's perspective). For the rare case where a user is demoted between two consecutive saves, the worst case is one rejected `chat_config` write with `AuthorizationError` — acceptable.
- **Migration backfill omits chats users only admin** (have never messaged in) → those chats won't appear in the list until the admin refresh fires on first settings load. Mitigation: the list-endpoint refresh discovers and upserts these on the next visit, which is when the user would notice anyway.
- **Frontend churn** → `ChatSettingsPage` and the `useChats` hook need substantial restructuring (the response shape changes from flat to nested). Mitigation: nested shape mirrors the editing surfaces in the UI, so the refactor should clarify rather than complicate.
- **Wider test impact** than usual: 40+ test files set `use_about_me=True` directly on `chat_config` in test fixtures. Mitigation: most occurrences are in fixture builders that can be edited centrally; a follow-up grep at the end of the implementation confirms zero stragglers.
- **Down-migration is lossy** → reverting drops the per-user preference granularity, restoring chat-wide `True` defaults. Mitigation: documented in the migration file; production rollback would lose privacy state, but this is acceptable for a one-way correctness fix.

## Migration Plan

1. **Backend deploy** (atomic):
   - Run Alembic migration (creates table, backfills, drops columns).
   - Deploy new code with new endpoints active and old endpoints removed.
2. **Web app deploy** (immediately after):
   - Update API client (`chat-settings-service.ts`, `user-settings-service.ts`).
   - Update `ChatSettingsPage` to read/write nested shape.
   - Update `useChats` to consume the new full-settings list response.
3. **Verification**:
   - Smoke test: existing users see their chats with their previous flags (`True/True` from migration), can toggle, can save.
   - Smoke test: a non-admin in a group chat can now see and toggle their own preferences.
   - Smoke test: a non-admin trying to save `chat_config` fields gets `AuthorizationError`.

**Rollback**: revert backend deploy + run down-migration. Web app needs to revert too. Lossy on per-user preferences (Decision #7 risk). Acceptable for an immediate post-deploy rollback window.
