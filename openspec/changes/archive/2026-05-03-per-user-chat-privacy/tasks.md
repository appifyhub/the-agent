## 1. Database layer

- [x] 1.1 Create `src/db/model/chat_membership.py` with `ChatMembershipDB` model: composite PK `(user_id, chat_id)`, FK to `simulants.id` and `chat_configs.chat_id`, `is_admin` (bool, default false), `use_about_me` (bool, default true), `use_custom_prompt` (bool, default true)
- [x] 1.2 Create `src/features/chat/membership/chat_membership.py` with `ChatMembership` domain dataclass (`@dataclass(kw_only=True)`); create `chat_membership_mapper.py` with `db()` / `domain()` converter functions; create `chat_membership_repo.py` with `ChatMembershipRepository` — `get`, `get_all_for_user`, `get_all_for_chat`, `save` (upsert by composite PK), `delete`; all signatures use `ChatMembership` domain object, never `ChatMembershipDB`
- [x] 1.3 ~~Create `src/db/crud/chat_membership.py`~~ — superseded by 1.2 (Repository pattern; no CRUD/schema files created)
- [x] 1.4 Remove `use_about_me` and `use_custom_prompt` columns from `src/db/model/chat_config.py`
- [x] 1.5 Remove `use_about_me` and `use_custom_prompt` fields from `src/db/schema/chat_config.py` (`ChatConfigBase`)
- [x] 1.6 Add `ChatMembershipDB` import to `src/db/alembic/env.py` so autogenerate detects the new model
- [x] 1.7 Wire `chat_membership_repo` (`ChatMembershipRepository`) into `src/di/di.py` and expose via `chat_membership_repo` property; add `chat_membership_repo()` factory to `test/db/sql_util.py`

## 2. Database migration

- [x] 2.1 Ask the user to run `./tools/db_generate_migration.sh -y` to generate the Alembic migration; confirm autogenerate produced the create-table and drop-column ops
- [x] 2.2 Hand-edit the generated migration's `upgrade()` to add the SQL backfill from `chat_messages` (defaults: `use_about_me=true`, `use_custom_prompt=true`; `is_admin=true` only when chat is private AND `external_id` matches user's `telegram_chat_id` or `whatsapp_user_id`); use `ON CONFLICT (user_id, chat_id) DO NOTHING`
- [x] 2.3 Order operations in `upgrade()`: create table → backfill → drop columns
- [x] 2.4 Implement `downgrade()` to restore the two columns on `chat_configs` with `NOT NULL DEFAULT true` and drop `chat_memberships`; add a comment noting per-user granularity is lost on rollback
- [x] 2.5 Ask the user to run `./tools/db_apply_migration.sh` after they review the migration

## 3. Prompt resolver gate

- [x] 3.1 Update `src/features/chat/chat_agent.py` to look up the invoker's `ChatMembership` via `di.chat_membership_repo.get(invoker.id, target_chat.chat_id)` and pass it as a parameter to `prompt_resolvers.chat()`
- [x] 3.2 Add `invoker_membership: ChatMembership | None` parameter to `prompt_resolvers.chat()`; replace `target_chat.use_about_me` check with `invoker_membership and invoker_membership.use_about_me` (null → false, no injection)
- [x] 3.3 Replace `target_chat.use_custom_prompt` check with `invoker_membership and invoker_membership.use_custom_prompt` (same semantics)
- [x] 3.4 Verify no other call sites read `chat_config.use_about_me` or `chat_config.use_custom_prompt` (grep across `src/`)

## 4. First-message membership upsert

- [x] 4.1 In `src/features/chat/telegram/telegram_data_resolver.py`, drop the lines that copy/set `use_about_me` and `use_custom_prompt` on `ChatConfigSave`
- [x] 4.2 In the same resolver, add `__ensure_membership(user, chat)` — calls `di.chat_membership_repo.get()`; if no row, calls `di.chat_membership_repo.save(ChatMembership(...))` with defaults `use_about_me=True`, `use_custom_prompt=True`, `is_admin=False`; invoked after persisting user + chat config, skipped for the agent user (`is_the_agent` check)
- [x] 4.3 Mirror the same changes in `src/features/chat/whatsapp/whatsapp_data_resolver.py`
- [x] 4.4 Confirm the upsert path does NOT call `getChatAdministrators` or any platform admin API

## 5. Authorization service split

- [x] 5.1 Add `validate_chat_member(user, chat) -> ChatMembership` to `src/api/authorization_service.py`: uses `di.chat_membership_repo.get()`; creates on-the-fly with `(is_admin=False, use_about_me=False, use_custom_prompt=False)` defaults via `di.chat_membership_repo.save()` if missing; returns `ChatMembership` domain object
- [x] 5.2 Add `validate_chat_admin(user, chat) -> ChatMembership` that wraps the existing admin check (`get_authorized_chats` + chat-id filter); calls `di.chat_membership_repo.save(ChatMembership(...))` to update `is_admin` if the flag has drifted; raises `AuthorizationError(NOT_CHAT_ADMIN)` if not admin
- [x] 5.3 Keep `get_authorized_chats(user)` available as the helper used by the list-fetch admin refresh
- [x] 5.4 Add `refresh_admin_status_for_user(user) -> list[ChatMembership]`: runs `get_authorized_chats`; for each admin chat, calls `di.chat_membership_repo.save(ChatMembership(...))` to upsert or flip `is_admin`; returns the final list of `ChatMembership` domain objects via `di.chat_membership_repo.get_all_for_user()`

## 6. API models and mappers

- [x] 6.1 Create `src/api/model/chat_config_response.py` with the `chat_config` portion: `chat_id, title, platform, language_iso_code, language_name, is_private, is_own, is_admin, reply_chance_percent, release_notifications, media_mode`
- [x] 6.2 Create `src/api/model/user_chat_config_response.py` with `use_about_me, use_custom_prompt`
- [x] 6.3 Replace `src/api/model/chat_settings_response.py` to wrap both: `ChatSettingsResponse { chat_config, user_chat_config }`
- [x] 6.4 Create `src/api/model/chat_config_payload.py` with the admin-editable fields (`language_name, language_iso_code, reply_chance_percent, release_notifications, media_mode`); keep the existing field validators for trimming and reply-chance bounds
- [x] 6.5 Create `src/api/model/user_chat_config_payload.py` with `use_about_me, use_custom_prompt`
- [x] 6.6 Replace `src/api/model/chat_settings_payload.py` with `ChatSettingsPayload { chat_config: ChatConfigPayload | None, user_chat_config: UserChatConfigPayload | None }`; reject empty bodies (both `None`) at validation time with a clear error code (enforced in controller)
- [x] 6.7 Replace `src/api/mapper/chat_mapper.py:domain_to_api` with a function that takes `(chat: ChatConfig, membership: ChatMembership, is_own: bool)` and returns the nested `ChatSettingsResponse`
- [x] 6.8 Delete `ChatInfo` (the lean list item) from the API models — list items now use the same `ChatSettingsResponse` (no `ChatInfo` class existed in backend src/; list endpoint returned plain dicts)

## 7. Settings controller

- [x] 7.1 Replace `fetch_admin_chats` in `src/api/settings_controller.py` with `fetch_user_chats(user_id_hex) -> list[dict]`: validates invoker can act on the target user, runs `refresh_admin_status_for_user`, then loads all membership rows for the user, joins to chat configs, and returns the array of full nested settings (sorted as today: private/own first, then chat type, then title)
- [x] 7.2 Add `fetch_chat_settings_for_user(user_id_hex, chat_id) -> dict`: validates invoker can act on the target user, calls `validate_chat_member` (creates row if needed), refreshes admin status for this single chat, returns the nested response
- [x] 7.3 Replace `save_chat_settings(chat_id, payload)` with `save_chat_settings_for_user(user_id_hex, chat_id, payload)`: rejects when both payload sections are absent; if `chat_config` present, calls `validate_chat_admin` and updates `chat_configs`; always handles `user_chat_config` via the membership row upsert
- [x] 7.4 Remove the legacy `use_about_me` / `use_custom_prompt` validation block (now lives in the user_chat_config payload)
- [x] 7.5 Remove dead error codes that no longer fire (`INVALID_USE_ABOUT_ME`, `INVALID_USE_CUSTOM_PROMPT`) from `util/error_codes.py`

## 8. HTTP routes

- [x] 8.1 In `src/main.py`, add `GET /user/{user_id}/chats/{chat_id}` → `fetch_chat_settings_for_user`
- [x] 8.2 In `src/main.py`, add `PATCH /user/{user_id}/chats/{chat_id}` → `save_chat_settings_for_user`
- [x] 8.3 Update existing `GET /user/{resource_id}/chats` handler to call the new `fetch_user_chats` (response shape changes from `list[ChatInfo]` to `list[ChatSettingsResponse]`)
- [x] 8.4 Remove `PATCH /settings/chat/{chat_id}` route
- [x] 8.5 Replace `GET /settings/{settings_type}/{resource_id}` with `GET /settings/user/{resource_id}` (chat branch retired); `SettingsType` literal kept only for internal use in deep-link generation

## 9. Tests — backend

- [x] 9.1 Sweep `test/` for `use_about_me=` / `use_custom_prompt=` references in `ChatConfig`/`ChatConfigSave` fixtures; relocate them onto `ChatMembership` test fixtures (~40+ files: `test/api/`, `test/db/crud/`, `test/features/chat/**`)
- [x] 9.2 Add `test/features/chat/membership/test_chat_membership_repo.py` (get/save/upsert/get-by-user using real SQLite via `sql_util.chat_membership_repo()`) and `test_chat_membership_mapper.py` (db↔domain roundtrip)
- [x] 9.3 Update `test/api/test_authorization_service.py` to cover `validate_chat_member` (member, non-member, missing-row creation) and `validate_chat_admin` (admin success, non-admin denial, admin status persisted on membership row); mock uses `ChatMembershipRepository` spec and `ChatMembership` domain objects throughout
- [x] 9.4 Update `test/api/test_settings_controller.py` to cover the three new flows: `fetch_user_chats` (member-only chats appear; admin discovery upserts; sort order), `fetch_chat_settings_for_user` (creates row with false defaults on first fetch), `save_chat_settings_for_user` (member-only saves preferences; admin saves both; non-admin chat_config write rejected; empty body rejected)
- [x] 9.5 Update `test/api/mapper/test_chat_mapper.py` for the new `(chat, membership, is_own)` signature and nested response shape; `ChatMembership` imported from `features.chat.membership.chat_membership`
- [x] 9.6 Update `test/api/test_chat_settings_payload.py` for the nested `ChatConfigPayload` + `UserChatConfigPayload` model shape; empty-body test verifies both sections are `None` (controller rejects at runtime)
- [x] 9.7 Update prompt resolver tests (`test/features/...prompt_resolver*` and any tests calling the composer) to use membership-based fixtures and verify the no-row → no-injection path
- [x] 9.8 Update Telegram + WhatsApp data resolver tests (`test/features/chat/telegram/test_telegram_data_resolver.py`, `test/features/chat/whatsapp/test_whatsapp_data_resolver.py`) — wire `mock_di.chat_membership_repo = self.sql.chat_membership_repo()` (already done); assert the membership upsert occurs and `chat_config` no longer carries the two booleans
- [x] 9.9 Run `pipenv run pre-commit run --all-files --show-diff-on-failure` and address linter errors

## 10. OpenAPI documentation

- [x] 10.1 In `docs/open-api-docs.yaml`, remove the `PATCH /settings/chat/{chat_id}` path
- [x] 10.2 Update `GET /settings/{settings_type}/{resource_id}` to enumerate `[user]` only and drop `ChatSettingsResponse` from the `oneOf`
- [x] 10.3 Update `GET /user/{resource_id}/chats` description and response: items now reference `ChatSettingsResponse` instead of `ChatInfo`
- [x] 10.4 Add path entries for `GET /user/{user_id}/chats/{chat_id}` and `PATCH /user/{user_id}/chats/{chat_id}`
- [x] 10.5 Replace `ChatSettingsResponse` schema with the nested form: `{ chat_config: ChatConfigResponse, user_chat_config: UserChatConfigResponse }`
- [x] 10.6 Replace `ChatSettingsPayload` schema with the nested form: `{ chat_config?: ChatConfigPayload, user_chat_config?: UserChatConfigPayload }`
- [x] 10.7 Add new schemas: `ChatConfigResponse` (with `is_admin`), `UserChatConfigResponse`, `ChatConfigPayload`, `UserChatConfigPayload`
- [x] 10.8 Remove the `ChatInfo` schema
- [x] 10.9 Bump the `info.version` in the YAML to reflect the breaking change

## 11. Frontend handoff

- [x] 11.1 Verify `../agent-web/CHANGELOG.md` (created during proposal phase) accurately reflects the final endpoint and schema deltas, including new error codes (`EMPTY_CHAT_SETTINGS_PAYLOAD = 1038`, removed `INVALID_USE_ABOUT_ME = 1006`, removed `INVALID_USE_CUSTOM_PROMPT = 1036`); update if anything drifted during implementation
- [x] 11.2 Confirm with the user that the agent-web team is aware of the breaking change and prepared to deploy in lockstep

## 12. Verification

- [x] 12.1 Run the full backend test suite (`pipenv run python -m pytest`) — all green
- [x] 12.2 Bring up dev server (`pipenv run python src/main.py --dev`); manually exercise: list (admin discovery), detail (auto-create with false defaults), patch (member-only, admin-only, mixed)
- [x] 12.3 Confirm `chat_configs` table no longer has the two columns and `chat_memberships` exists with the expected backfill row count
- [x] 12.4 Bump project version in `pyproject.toml` and write a release-notes entry
