## Why

Today, chat admins control whether `about_me` and `custom_prompt` get used **for every participant** in a chat — those toggles live on the chat config, not on the user. This is a privacy gap: an admin can force the bot to use another user's personal data, or block a user from having their own data used in the bot's responses. We need each user to control their own data per chat.

A second, related problem: the chat list endpoint only returns chats where the user is an admin. Non-admin members have no surface to set their own preferences because they don't see the chat at all.

## What Changes

- **BREAKING**: Per-user privacy controls replace the per-chat ones.
  - New `chat_memberships` table keyed on `(user_id, chat_id)` storing `use_about_me`, `use_custom_prompt`, and `is_admin`.
  - `chat_configs.use_about_me` and `chat_configs.use_custom_prompt` columns dropped.
- Prompt resolution (`prompt_resolvers.py`) reads the invoker's `chat_memberships` row instead of the chat config; if no row exists, both flags default to `false`.
- First messaging interaction in a chat upserts a `chat_memberships` row with `True` defaults (membership is implicit on participation).
- Admin status is stored in `chat_memberships` and refreshed lazily on settings list/detail fetches (no extra cost on the messaging path).
- **BREAKING**: Chat settings REST surface is restructured under the user.
  - `GET /user/{user_id}/chats` — returns array of full settings per chat (was: minimal `ChatInfo`).
  - `GET /user/{user_id}/chats/{chat_id}` — new, returns full settings for one chat (creates membership row on the fly with `false` defaults if missing).
  - `PATCH /user/{user_id}/chats/{chat_id}` — new, accepts nested `{chat_config, user_chat_config}` payload.
  - `GET /settings/chat/{chat_id}` (via `/settings/{settings_type}/{resource_id}`) and `PATCH /settings/chat/{chat_id}` retire.
- Authorization split: `user_chat_config` writes allowed for any member; `chat_config` writes still require `is_admin`.
- Response/payload shape becomes nested: `chat_config` (existing fields plus `is_admin`) + `user_chat_config` (`use_about_me`, `use_custom_prompt`).
- One Alembic migration creates `chat_memberships`, seeds it from `chat_messages` history (defaults `True` for both flags; `is_admin=True` only for own private chats by `external_id` match), and drops the two columns from `chat_configs`.
- OpenAPI docs (`docs/open-api-docs.yaml`) updated to reflect new endpoints, retired endpoints, and nested schemas.
- Frontend handoff: a `CHANGELOG.md` is written in `../agent-web` documenting endpoint and schema deltas for the web team.

## Capabilities

### New Capabilities

- `chat-membership`: per-user-per-chat record carrying privacy preferences (`use_about_me`, `use_custom_prompt`) and cached admin status; defines lifecycle (creation on first message, lazy admin refresh, virtual-default behavior when no row exists) and how prompt resolution consumes it.
- `chat-settings-api`: user-scoped REST contract for chat settings — list/detail/save endpoints under `/user/{user_id}/chats[/{chat_id}]`, nested `chat_config` + `user_chat_config` payload/response shape, and the authorization rules separating chat-wide changes (admin-only) from per-user preferences (any member).

### Modified Capabilities

_(None — no existing specs.)_

## Impact

**Database**
- New table `chat_memberships` (PK: `user_id`, `chat_id`).
- `chat_configs.use_about_me` and `chat_configs.use_custom_prompt` columns dropped.
- Single Alembic migration handles create + backfill from `chat_messages` + drop.

**Code**
- `db/model/chat_config.py`, `db/schema/chat_config.py` — column removals.
- `db/model/chat_membership.py` — new SQLAlchemy DB model (table schema only).
- `features/chat/membership/chat_membership.py` — new domain dataclass (`@dataclass(kw_only=True)`).
- `features/chat/membership/chat_membership_mapper.py` — `db()` / `domain()` converter functions.
- `features/chat/membership/chat_membership_repo.py` — `ChatMembershipRepository` (get, get_all_for_user, save/upsert, delete); all method signatures use the domain dataclass, not DB models.
- `features/integrations/prompt_resolvers.py` — switch from chat-config flags to membership lookup with `false` virtual default.
- `features/chat/telegram/telegram_data_resolver.py`, `features/chat/whatsapp/whatsapp_data_resolver.py` — drop the per-chat toggle preservation; upsert membership via repository on first interaction with `True` defaults.
- `api/settings_controller.py` — replace `fetch_admin_chats`, `fetch_chat_settings`, `save_chat_settings` with the new user-scoped flow; introduce membership-creation and lazy `is_admin` refresh.
- `api/authorization_service.py` — add `validate_chat_member` separate from existing `authorize_for_chat` (admin); reuse `get_authorized_chats` only as the admin-refresh helper.
- `api/mapper/chat_mapper.py`, `api/model/chat_settings_response.py`, `api/model/chat_settings_payload.py` — restructure into nested `chat_config` + `user_chat_config`.
- `main.py` — register new routes, retire old ones, update the `SettingsType` branch.
- `di/di.py` — wire `chat_membership_repo` (Repository, not CRUD).

**API**
- New: `GET /user/{user_id}/chats/{chat_id}`, `PATCH /user/{user_id}/chats/{chat_id}`.
- Changed shape: `GET /user/{user_id}/chats` (now full settings per item).
- Retired: `PATCH /settings/chat/{chat_id}`, plus the `chat` branch of `GET /settings/{settings_type}/{resource_id}`.
- All schemas in `docs/open-api-docs.yaml` updated; `ChatInfo` retired.

**Tests**
- All tests referencing `chat_config.use_about_me` / `chat_config.use_custom_prompt` (40+ occurrences across `test/api`, `test/db/crud`, `test/features`) need to relocate those fields onto `ChatMembership`.
- New tests for `ChatMembershipRepository` (repo + mapper), membership-aware prompt resolution, lazy admin refresh, and the new endpoints.

**Docs / Frontend handoff**
- `docs/open-api-docs.yaml` — full update.
- `../agent-web/CHANGELOG.md` — new file documenting endpoint and schema changes for the web team.

**Backwards compatibility**: Breaking. Existing API clients hitting `PATCH /settings/chat/{chat_id}` will fail; the web app must be updated to call the new endpoints in lockstep.
