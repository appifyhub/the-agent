from api.model.user_settings_payload import UserSettingsPayload
from api.model.user_settings_response import UserSettingsResponse
from db.schema.user import User, UserSave
from util.functions import mask_secret


def api_to_domain(payload: UserSettingsPayload, existing_user: User) -> UserSave:
    user_save = UserSave(**existing_user.model_dump())

    # Update token fields directly - payload constructor validation already handled empty string → None conversion
    if payload.open_ai_key is not None:
        user_save.open_ai_key = payload.open_ai_key if payload.open_ai_key.strip() else None
    if payload.anthropic_key is not None:
        user_save.anthropic_key = payload.anthropic_key if payload.anthropic_key.strip() else None
    if payload.google_ai_key is not None:
        user_save.google_ai_key = payload.google_ai_key if payload.google_ai_key.strip() else None
    if payload.perplexity_key is not None:
        user_save.perplexity_key = payload.perplexity_key if payload.perplexity_key.strip() else None
    if payload.replicate_key is not None:
        user_save.replicate_key = payload.replicate_key if payload.replicate_key.strip() else None
    if payload.rapid_api_key is not None:
        user_save.rapid_api_key = payload.rapid_api_key if payload.rapid_api_key.strip() else None
    if payload.coinmarketcap_key is not None:
        user_save.coinmarketcap_key = payload.coinmarketcap_key if payload.coinmarketcap_key.strip() else None

    # Update tool choice fields - payload constructor validation already handled empty string → None conversion
    if payload.tool_choice_chat is not None:
        user_save.tool_choice_chat = payload.tool_choice_chat if payload.tool_choice_chat.strip() else None
    if payload.tool_choice_reasoning is not None:
        user_save.tool_choice_reasoning = payload.tool_choice_reasoning if payload.tool_choice_reasoning.strip() else None
    if payload.tool_choice_copywriting is not None:
        user_save.tool_choice_copywriting = payload.tool_choice_copywriting if payload.tool_choice_copywriting.strip() else None
    if payload.tool_choice_vision is not None:
        user_save.tool_choice_vision = payload.tool_choice_vision if payload.tool_choice_vision.strip() else None
    if payload.tool_choice_hearing is not None:
        user_save.tool_choice_hearing = payload.tool_choice_hearing if payload.tool_choice_hearing.strip() else None
    if payload.tool_choice_images_gen is not None:
        user_save.tool_choice_images_gen = payload.tool_choice_images_gen if payload.tool_choice_images_gen.strip() else None
    if payload.tool_choice_images_edit is not None:
        user_save.tool_choice_images_edit = payload.tool_choice_images_edit if payload.tool_choice_images_edit.strip() else None
    if payload.tool_choice_images_restoration is not None:
        user_save.tool_choice_images_restoration = (
            payload.tool_choice_images_restoration if payload.tool_choice_images_restoration.strip() else None
        )
    if payload.tool_choice_images_inpainting is not None:
        user_save.tool_choice_images_inpainting = (
            payload.tool_choice_images_inpainting if payload.tool_choice_images_inpainting.strip() else None
        )
    if payload.tool_choice_images_background_removal is not None:
        user_save.tool_choice_images_background_removal = (
            payload.tool_choice_images_background_removal if payload.tool_choice_images_background_removal.strip() else None
        )
    if payload.tool_choice_search is not None:
        user_save.tool_choice_search = payload.tool_choice_search if payload.tool_choice_search.strip() else None
    if payload.tool_choice_embedding is not None:
        user_save.tool_choice_embedding = payload.tool_choice_embedding if payload.tool_choice_embedding.strip() else None
    if payload.tool_choice_api_fiat_exchange is not None:
        user_save.tool_choice_api_fiat_exchange = (
            payload.tool_choice_api_fiat_exchange if payload.tool_choice_api_fiat_exchange.strip() else None
        )
    if payload.tool_choice_api_crypto_exchange is not None:
        user_save.tool_choice_api_crypto_exchange = (
            payload.tool_choice_api_crypto_exchange if payload.tool_choice_api_crypto_exchange.strip() else None
        )
    if payload.tool_choice_api_twitter is not None:
        user_save.tool_choice_api_twitter = payload.tool_choice_api_twitter if payload.tool_choice_api_twitter.strip() else None

    return user_save


def domain_to_api(user: User) -> UserSettingsResponse:
    return UserSettingsResponse(
        id = user.id.hex,
        full_name = user.full_name,
        telegram_username = user.telegram_username,
        telegram_chat_id = user.telegram_chat_id,
        telegram_user_id = user.telegram_user_id,
        open_ai_key = mask_secret(user.open_ai_key),
        anthropic_key = mask_secret(user.anthropic_key),
        google_ai_key = mask_secret(user.google_ai_key),
        perplexity_key = mask_secret(user.perplexity_key),
        replicate_key = mask_secret(user.replicate_key),
        rapid_api_key = mask_secret(user.rapid_api_key),
        coinmarketcap_key = mask_secret(user.coinmarketcap_key),
        tool_choice_chat = user.tool_choice_chat,
        tool_choice_reasoning = user.tool_choice_reasoning,
        tool_choice_copywriting = user.tool_choice_copywriting,
        tool_choice_vision = user.tool_choice_vision,
        tool_choice_hearing = user.tool_choice_hearing,
        tool_choice_images_gen = user.tool_choice_images_gen,
        tool_choice_images_edit = user.tool_choice_images_edit,
        tool_choice_images_restoration = user.tool_choice_images_restoration,
        tool_choice_images_inpainting = user.tool_choice_images_inpainting,
        tool_choice_images_background_removal = user.tool_choice_images_background_removal,
        tool_choice_search = user.tool_choice_search,
        tool_choice_embedding = user.tool_choice_embedding,
        tool_choice_api_fiat_exchange = user.tool_choice_api_fiat_exchange,
        tool_choice_api_crypto_exchange = user.tool_choice_api_crypto_exchange,
        tool_choice_api_twitter = user.tool_choice_api_twitter,
        group = user.group.value,
        created_at = user.created_at.isoformat(),
    )
