## ADDED Requirements

### Requirement: User-scoped chat list endpoint

The system SHALL expose `GET /user/{user_id}/chats` returning a JSON array where each element is a full chat settings object (same shape as the detail endpoint). The list MUST contain every chat where the invoker has a `ChatMembership` row, plus any chats discovered as administered during the lazy admin refresh. Items MUST be sorted deterministically (private/own first, then by chat type, then by title).

#### Scenario: List includes member chats

- **WHEN** the invoker fetches `GET /user/{user_id}/chats` and has membership rows in three chats
- **THEN** the response array contains three items, one per membership

#### Scenario: List discovers admin chats not yet in membership

- **WHEN** the invoker is admin in a chat where they have no membership row, and they fetch `GET /user/{user_id}/chats`
- **THEN** a membership row is created for that chat with `is_admin=true`, and the chat appears in the response

#### Scenario: List items carry full nested settings shape

- **WHEN** the response is parsed
- **THEN** each item has the structure `{ "chat_config": {...}, "user_chat_config": {...} }`

### Requirement: User-scoped chat detail endpoint

The system SHALL expose `GET /user/{user_id}/chats/{chat_id}` returning a single chat settings object with the nested `{chat_config, user_chat_config}` shape. The endpoint MUST permit any chat member (any user with — or eligible for — a `ChatMembership` row in this chat). If no row exists for the invoker, the endpoint MUST create one with privacy-safe defaults (`use_about_me=false`, `use_custom_prompt=false`, `is_admin=false`) and then run the admin refresh.

#### Scenario: Member fetches their settings

- **WHEN** an invoker with a membership row fetches `GET /user/{user_id}/chats/{chat_id}`
- **THEN** the response contains the chat's config and the invoker's preferences from their membership row

#### Scenario: First-time fetch by an existing chat participant

- **WHEN** an invoker fetches `GET /user/{user_id}/chats/{chat_id}` and has no membership row yet
- **THEN** a row is created with `use_about_me=false`, `use_custom_prompt=false`, `is_admin` set by the immediate admin refresh
- **AND** the response reflects those values

#### Scenario: Fetch by non-member with no admin access fails

- **WHEN** an invoker fetches `GET /user/{user_id}/chats/{chat_id}` for a chat they neither participate in nor administer
- **THEN** the system returns an authorization error

### Requirement: User-scoped chat save endpoint

The system SHALL expose `PATCH /user/{user_id}/chats/{chat_id}` accepting a JSON body of shape `{ "chat_config"?: {...}, "user_chat_config"?: {...} }`. Both keys are optional but at least one MUST be provided. `user_chat_config` writes MUST be permitted for any member; `chat_config` writes MUST require the invoker's `is_admin=true` for this chat. If `chat_config` is present and the invoker is not admin, the request MUST fail with `AuthorizationError` and no part of the payload may be persisted.

#### Scenario: Member saves only their preferences

- **WHEN** a non-admin member sends `PATCH` with `{"user_chat_config": {"use_about_me": false, "use_custom_prompt": true}}`
- **THEN** the membership row's flags are updated and the request succeeds

#### Scenario: Admin saves both sections atomically

- **WHEN** an admin sends `PATCH` with both `chat_config` and `user_chat_config`
- **THEN** chat-wide settings are updated AND the admin's own membership row is updated, in a single transaction

#### Scenario: Non-admin attempting chat_config write fails atomically

- **WHEN** a non-admin member sends `PATCH` with a `chat_config` section (with or without `user_chat_config`)
- **THEN** the request fails with an authorization error
- **AND** no fields from either section are persisted

#### Scenario: Empty payload is rejected

- **WHEN** a request body contains neither `chat_config` nor `user_chat_config`
- **THEN** the request fails with a validation error

### Requirement: Nested response and payload shape

The system SHALL use the nested `{chat_config, user_chat_config}` structure for both responses and PATCH payloads. `chat_config` MUST contain `chat_id`, `title`, `platform`, `language_iso_code`, `language_name`, `is_private`, `is_own`, `is_admin`, `reply_chance_percent`, `release_notifications`, `media_mode`. `user_chat_config` MUST contain `use_about_me` and `use_custom_prompt`. Privacy toggles MUST NOT appear inside `chat_config`.

#### Scenario: chat_config carries is_admin

- **WHEN** any GET response is parsed
- **THEN** `chat_config.is_admin` is present as a boolean

#### Scenario: Privacy flags only appear under user_chat_config

- **WHEN** any GET response is parsed
- **THEN** `chat_config` MUST NOT contain `use_about_me` or `use_custom_prompt`
- **AND** `user_chat_config` MUST contain both fields as booleans

### Requirement: Retirement of chat-keyed settings endpoints

The system SHALL remove the `PATCH /settings/chat/{chat_id}` endpoint. The `GET /settings/{settings_type}/{resource_id}` endpoint SHALL no longer accept `settings_type=chat`.

#### Scenario: Retired PATCH endpoint returns 404

- **WHEN** any client sends `PATCH /settings/chat/{chat_id}`
- **THEN** the server responds with `404 Not Found`

#### Scenario: GET settings/chat path is no longer routed

- **WHEN** any client sends `GET /settings/chat/{chat_id}`
- **THEN** the server responds with `404 Not Found` (or `422` if validation rejects `chat` as a `settings_type`)

### Requirement: OpenAPI documentation updated

The system's `docs/open-api-docs.yaml` SHALL be updated in lockstep with the API change: the new endpoints documented, retired endpoints removed, the `ChatInfo` schema removed, and `ChatSettingsResponse` / `ChatSettingsPayload` restructured to the nested shape with `is_admin` added to `chat_config`.

#### Scenario: OpenAPI lists the new endpoints

- **WHEN** `docs/open-api-docs.yaml` is parsed after this change
- **THEN** it contains path entries for `GET /user/{user_id}/chats/{chat_id}` and `PATCH /user/{user_id}/chats/{chat_id}`

#### Scenario: OpenAPI no longer lists retired endpoints

- **WHEN** `docs/open-api-docs.yaml` is parsed after this change
- **THEN** the path entry for `PATCH /settings/chat/{chat_id}` is absent
- **AND** the `ChatInfo` schema definition is absent
