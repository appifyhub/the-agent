from typing import List

from pydantic import BaseModel

from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.chat_message import ChatMessage, ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachment, ChatMessageAttachmentSave
from db.schema.user import User, UserSave
from di.di import DI
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from util import log
from util.config import config
from util.functions import is_the_agent


class TelegramDataResolver:
    """
    Resolves the final set of data attributes ready to be used by the service.
    If needed, this resolver will fetch more data from the API or the database.
    """

    class Result(BaseModel):
        chat: ChatConfig
        author: User | None
        message: ChatMessage
        attachments: List[ChatMessageAttachment]

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def resolve(self, mapping_result: TelegramDomainMapper.Result) -> Result:
        log.t(f"Resolving mapping result: {mapping_result}")
        resolved_chat_config = self.resolve_chat_config(mapping_result.chat)
        resolved_author: User | None = None
        if mapping_result.author:
            if is_the_agent(mapping_result.author):
                mapping_result.author.telegram_chat_id = None  # bot has no private chat
            resolved_author = self.resolve_author(mapping_result.author)
            if resolved_author:
                mapping_result.message.author_id = resolved_author.id
        # we need to set the resolved chat's UUID to the message and attachments
        mapping_result.message.chat_id = resolved_chat_config.chat_id
        for attachment in mapping_result.attachments:
            attachment.chat_id = resolved_chat_config.chat_id
        resolved_chat_message = self.resolve_chat_message(mapping_result.message)
        resolved_attachments = [self.resolve_chat_message_attachment(attachment) for attachment in mapping_result.attachments]
        return TelegramDataResolver.Result(
            chat = resolved_chat_config,
            author = resolved_author,
            message = resolved_chat_message,
            attachments = resolved_attachments,
        )

    def resolve_chat_config(self, mapped_data: ChatConfigSave) -> ChatConfig:
        log.t(f"  Resolving chat config: {mapped_data}")
        old_chat_config_db = self.__di.chat_config_crud.get_by_external_identifiers(
            external_id = str(mapped_data.external_id),
            chat_type = mapped_data.chat_type,
        )
        if old_chat_config_db:
            old_chat_config = ChatConfig.model_validate(old_chat_config_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.chat_id = old_chat_config.chat_id
            mapped_data.language_iso_code = old_chat_config.language_iso_code
            mapped_data.language_name = old_chat_config.language_name
            mapped_data.is_private = old_chat_config.is_private
            mapped_data.reply_chance_percent = old_chat_config.reply_chance_percent
            mapped_data.release_notifications = old_chat_config.release_notifications
        return ChatConfig.model_validate(self.__di.chat_config_crud.save(mapped_data))

    # noinspection DuplicatedCode
    def resolve_author(self, mapped_data: UserSave | None) -> User | None:
        if not mapped_data:
            return None
        log.t(f"  Resolving user: {mapped_data}")
        old_user_db = (
            self.__di.user_crud.get_by_telegram_user_id(mapped_data.telegram_user_id or -1) or
            self.__di.user_crud.get_by_telegram_username(mapped_data.telegram_username or "")
        )

        if old_user_db:
            old_user = User.model_validate(old_user_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.id = old_user.id
            mapped_data.telegram_chat_id = mapped_data.telegram_chat_id or old_user.telegram_chat_id
            mapped_data.open_ai_key = old_user.open_ai_key
            mapped_data.anthropic_key = old_user.anthropic_key
            mapped_data.google_ai_key = old_user.google_ai_key
            mapped_data.perplexity_key = old_user.perplexity_key
            mapped_data.replicate_key = old_user.replicate_key
            mapped_data.rapid_api_key = old_user.rapid_api_key
            mapped_data.coinmarketcap_key = old_user.coinmarketcap_key
            mapped_data.tool_choice_chat = old_user.tool_choice_chat
            mapped_data.tool_choice_reasoning = old_user.tool_choice_reasoning
            mapped_data.tool_choice_copywriting = old_user.tool_choice_copywriting
            mapped_data.tool_choice_vision = old_user.tool_choice_vision
            mapped_data.tool_choice_hearing = old_user.tool_choice_hearing
            mapped_data.tool_choice_images_gen = old_user.tool_choice_images_gen
            mapped_data.tool_choice_images_edit = old_user.tool_choice_images_edit
            mapped_data.tool_choice_images_restoration = old_user.tool_choice_images_restoration
            mapped_data.tool_choice_images_inpainting = old_user.tool_choice_images_inpainting
            mapped_data.tool_choice_images_background_removal = old_user.tool_choice_images_background_removal
            mapped_data.tool_choice_search = old_user.tool_choice_search
            mapped_data.tool_choice_embedding = old_user.tool_choice_embedding
            mapped_data.tool_choice_api_fiat_exchange = old_user.tool_choice_api_fiat_exchange
            mapped_data.tool_choice_api_crypto_exchange = old_user.tool_choice_api_crypto_exchange
            mapped_data.tool_choice_api_twitter = old_user.tool_choice_api_twitter
            mapped_data.group = old_user.group
        else:
            # new users can only be added until the user limit is reached
            user_count = self.__di.user_crud.count()
            if user_count >= config.max_users:
                raise ValueError(log.e(f"User limit reached: {user_count}/{config.max_users}. Try again later"))

        # reset token values to None so that there's no confusion going forward
        def is_empty_secret(secret):
            if not secret:
                return True
            if hasattr(secret, "get_secret_value"):
                return not secret.get_secret_value().strip()
            return not secret.strip() if isinstance(secret, str) else False

        # reset all SecretStr fields that are empty
        api_key_fields = mapped_data._get_secret_str_fields()
        for field_name in api_key_fields:
            field_value = getattr(mapped_data, field_name)
            if is_empty_secret(field_value):
                setattr(mapped_data, field_name, None)
        # reset tool choice values to None if they are empty strings
        if not mapped_data.tool_choice_chat or not mapped_data.tool_choice_chat.strip():
            mapped_data.tool_choice_chat = None
        if not mapped_data.tool_choice_reasoning or not mapped_data.tool_choice_reasoning.strip():
            mapped_data.tool_choice_reasoning = None
        if not mapped_data.tool_choice_copywriting or not mapped_data.tool_choice_copywriting.strip():
            mapped_data.tool_choice_copywriting = None
        if not mapped_data.tool_choice_vision or not mapped_data.tool_choice_vision.strip():
            mapped_data.tool_choice_vision = None
        if not mapped_data.tool_choice_hearing or not mapped_data.tool_choice_hearing.strip():
            mapped_data.tool_choice_hearing = None
        if not mapped_data.tool_choice_images_gen or not mapped_data.tool_choice_images_gen.strip():
            mapped_data.tool_choice_images_gen = None
        if not mapped_data.tool_choice_images_edit or not mapped_data.tool_choice_images_edit.strip():
            mapped_data.tool_choice_images_edit = None
        if not mapped_data.tool_choice_images_restoration or not mapped_data.tool_choice_images_restoration.strip():
            mapped_data.tool_choice_images_restoration = None
        if not mapped_data.tool_choice_images_inpainting or not mapped_data.tool_choice_images_inpainting.strip():
            mapped_data.tool_choice_images_inpainting = None
        if not mapped_data.tool_choice_images_background_removal or not mapped_data.tool_choice_images_background_removal.strip():
            mapped_data.tool_choice_images_background_removal = None
        if not mapped_data.tool_choice_search or not mapped_data.tool_choice_search.strip():
            mapped_data.tool_choice_search = None
        if not mapped_data.tool_choice_embedding or not mapped_data.tool_choice_embedding.strip():
            mapped_data.tool_choice_embedding = None
        if not mapped_data.tool_choice_api_fiat_exchange or not mapped_data.tool_choice_api_fiat_exchange.strip():
            mapped_data.tool_choice_api_fiat_exchange = None
        if not mapped_data.tool_choice_api_crypto_exchange or not mapped_data.tool_choice_api_crypto_exchange.strip():
            mapped_data.tool_choice_api_crypto_exchange = None
        if not mapped_data.tool_choice_api_twitter or not mapped_data.tool_choice_api_twitter.strip():
            mapped_data.tool_choice_api_twitter = None
        return User.model_validate(self.__di.user_crud.save(mapped_data))

    def resolve_chat_message(self, mapped_data: ChatMessageSave) -> ChatMessage:
        log.t(f"  Resolving chat message: {mapped_data}")
        assert mapped_data.chat_id is not None
        old_chat_message_db = self.__di.chat_message_crud.get(mapped_data.chat_id, mapped_data.message_id)
        if old_chat_message_db:
            old_chat_message = ChatMessage.model_validate(old_chat_message_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.chat_id = old_chat_message.chat_id
            mapped_data.author_id = mapped_data.author_id or old_chat_message.author_id
            mapped_data.sent_at = mapped_data.sent_at or old_chat_message.sent_at
        return ChatMessage.model_validate(self.__di.chat_message_crud.save(mapped_data))

    def resolve_chat_message_attachment(self, mapped_data: ChatMessageAttachmentSave) -> ChatMessageAttachment:
        log.t(f"  Resolving chat message attachment: {mapped_data}")
        old_attachment_db = None
        if mapped_data.external_id:
            old_attachment_db = self.__di.chat_message_attachment_crud.get_by_external_id(mapped_data.external_id)

        if old_attachment_db:
            old_attachment = ChatMessageAttachment.model_validate(old_attachment_db)
            # reset the attributes that are not normally changed through the Telegram API
            mapped_data.id = old_attachment.id
            mapped_data.chat_id = old_attachment.chat_id
            mapped_data.size = mapped_data.size or old_attachment.size
            mapped_data.last_url = mapped_data.last_url or old_attachment.last_url
            mapped_data.last_url_until = mapped_data.last_url_until or old_attachment.last_url_until
            mapped_data.extension = mapped_data.extension or old_attachment.extension
            mapped_data.mime_type = mapped_data.mime_type or old_attachment.mime_type

        return self.__di.telegram_bot_sdk.refresh_attachment(attachment_save = mapped_data)
