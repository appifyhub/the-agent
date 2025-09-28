from datetime import datetime

from db.model.chat_config import ChatConfigDB
from db.schema.chat_config import ChatConfig, ChatConfigSave
from db.schema.user import User, UserSave
from features.integrations.integrations import resolve_agent_user
from features.prompting import prompt_composer, prompt_library
from features.prompting.prompt_composer import PromptFragment, PromptVar
from features.prompting.prompt_library import CHAT_MESSAGE_DELIMITER
from util.config import config

PLACEHOLDER_NO_DATA = "{undefined}"


def chat(
    invoker: User | UserSave,
    target_chat: ChatConfig | ChatConfigSave,
    tools_list: str | None,
) -> str:
    # add generic components to prepare the composer
    agent_user = resolve_agent_user(target_chat.chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.chat,
        prompt_library.styles.chat,
        prompt_library.personalities.chat_abot,
        prompt_library.tones.chat_abot,
        prompt_library.appendices.translate,
        prompt_library.metas.agent_username,
        prompt_library.metas.agent_website,
        prompt_library.metas.chat_title,
        prompt_library.metas.message_author,
        prompt_library.metas.today,
        prompt_library.metas.tools_list,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.language_name, target_chat.language_name or config.main_language_name),
        (PromptVar.language_iso, target_chat.language_iso_code or config.main_language_iso_code),
        (PromptVar.agent_website, config.website_url),
        (PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA),
        (PromptVar.author_name, invoker.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.author_role, invoker.group.value),
        (PromptVar.date_and_time, __now()),
        (PromptVar.tools_list, tools_list or PLACEHOLDER_NO_DATA),
    )
    # override and add platform-specific fragments and variables
    match target_chat.chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(prompt_library.formats.chat_telegram)
                .add_variables(
                    (PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA),
                    (PromptVar.author_username, invoker.telegram_username or PLACEHOLDER_NO_DATA),
                )
            ).render()
    raise ValueError(f"Unsupported chat type: {target_chat.chat_type}")


def copywriting_new_release_version(
    chat_type: ChatConfigDB.ChatType,
    target_chat: ChatConfig | ChatConfigSave | None,
) -> str:
    # add generic components to prepare the composer
    agent_user = resolve_agent_user(chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_new_release_version,
        prompt_library.appendices.translate,
        prompt_library.metas.agent_username,
        prompt_library.metas.agent_website,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.language_name, (target_chat and target_chat.language_name) or config.main_language_name),
        (PromptVar.language_iso, (target_chat and target_chat.language_iso_code) or config.main_language_iso_code),
        (PromptVar.agent_website, config.website_url),
        (PromptVar.date_and_time, __now()),
    )
    # add conditional generic components
    if target_chat:
        composer = (
            composer
            .add_fragments(prompt_library.metas.chat_title)
            .add_variables((PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA))
        )
    # override and add platform-specific fragments and variables
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(
                    prompt_library.styles.copywriting_new_release_version_chat,
                    prompt_library.formats.chat_telegram,
                    prompt_library.formats.copywriting_new_release_version_chat,
                )
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
        case ChatConfigDB.ChatType.github:
            return (
                composer
                .add_fragments(
                    prompt_library.styles.copywriting_new_release_version_github,
                    prompt_library.formats.post_github,
                    prompt_library.formats.copywriting_new_release_version_github,
                )
                .add_variables((PromptVar.agent_username, config.github_bot_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {chat_type}")


def copywriting_new_system_event(target_chat: ChatConfig | ChatConfigSave) -> str:
    # add generic components to prepare the composer
    agent_user = resolve_agent_user(target_chat.chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_new_system_event,
        prompt_library.styles.copywriting_system_announcement,
        prompt_library.personalities.chat_abot,
        prompt_library.appendices.translate,
        prompt_library.metas.agent_username,
        prompt_library.metas.chat_title,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.language_name, target_chat.language_name or config.main_language_name),
        (PromptVar.language_iso, target_chat.language_iso_code or config.main_language_iso_code),
        (PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA),
        (PromptVar.date_and_time, __now()),
    )
    # override and add platform-specific fragments and variables
    match target_chat.chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(prompt_library.formats.chat_telegram)
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {target_chat.chat_type}")


def copywriting_system_announcement(
    chat_type: ChatConfigDB.ChatType,
    target_chat: ChatConfig | ChatConfigSave | None,
) -> str:
    # prepare the correct message variant (broadcast vs personal)
    context_copywriting_variant: PromptFragment
    if target_chat:
        context_copywriting_variant = prompt_library.contexts.copywriting_developer_personal_message
    else:
        context_copywriting_variant = prompt_library.contexts.copywriting_broadcast_message

    # add generic components to prepare the composer
    agent_user = resolve_agent_user(chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        context_copywriting_variant,
        prompt_library.styles.copywriting_system_announcement,
        prompt_library.personalities.chat_abot,
        prompt_library.appendices.translate,
        prompt_library.metas.agent_username,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.language_name, (target_chat and target_chat.language_name) or config.main_language_name),
        (PromptVar.language_iso, (target_chat and target_chat.language_iso_code) or config.main_language_iso_code),
        (PromptVar.date_and_time, __now()),
    )
    # add conditional generic components
    if target_chat:
        composer = (
            composer
            .add_fragments(prompt_library.metas.chat_title)
            .add_variables((PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA))
        )
    # override and add platform-specific fragments and variables
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(prompt_library.formats.chat_telegram)
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {chat_type}")


def sentient_web_search(target_chat: ChatConfig | ChatConfigSave) -> str:
    agent_user = resolve_agent_user(target_chat.chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.sentient_web_search,
        prompt_library.styles.sentient_web_search,
        prompt_library.metas.agent_username,
        prompt_library.metas.chat_title,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA),
        (PromptVar.date_and_time, __now()),
    )
    match target_chat.chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(
                    prompt_library.formats.chat_telegram,
                    prompt_library.personalities.chat_abot,
                )
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {target_chat.chat_type}")


def copywriting_image_prompt_upscaler(chat_type: ChatConfigDB.ChatType) -> str:
    return prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_image_prompt_upscaler,
        prompt_library.styles.copywriting_image_prompt_upscaler,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, resolve_agent_user(chat_type).full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.date_and_time, __now()),
    ).render()


def computer_vision(chat_type: ChatConfigDB.ChatType) -> str:
    return prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.computer_vision,
        prompt_library.formats.computer_vision,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, resolve_agent_user(chat_type).full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.date_and_time, __now()),
    ).render()


def copywriting_computer_hearing(target_chat: ChatConfig | ChatConfigSave) -> str:
    # add generic components to prepare the composer
    agent_user = resolve_agent_user(target_chat.chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_computer_hearing,
        prompt_library.appendices.translate,
        prompt_library.metas.agent_username,
        prompt_library.metas.agent_website,
        prompt_library.metas.chat_title,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.personal_dictionary, __get_personal_dictionary(agent_user)),
        (PromptVar.language_name, (target_chat and target_chat.language_name) or config.main_language_name),
        (PromptVar.language_iso, (target_chat and target_chat.language_iso_code) or config.main_language_iso_code),
        (PromptVar.agent_website, config.website_url),
        (PromptVar.chat_title, target_chat.title or PLACEHOLDER_NO_DATA),
        (PromptVar.date_and_time, __now()),
    )
    # override and add platform-specific fragments and variables
    match target_chat.chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {target_chat.chat_type}")


def document_search_and_response(
    query: str | None,
    target_chat: ChatConfig | ChatConfigSave,
) -> str:
    agent_user = resolve_agent_user(target_chat.chat_type)
    return prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.document_search_and_response,
        prompt_library.appendices.translate,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.query, f"`{query}`" if query else PLACEHOLDER_NO_DATA),
        (PromptVar.personal_dictionary, __get_personal_dictionary(agent_user)),
        (PromptVar.language_name, (target_chat and target_chat.language_name) or config.main_language_name),
        (PromptVar.language_iso, (target_chat and target_chat.language_iso_code) or config.main_language_iso_code),
        (PromptVar.date_and_time, __now()),
    ).render()


def copywriting_support_request_title(chat_type: ChatConfigDB.ChatType) -> str:
    agent_user = resolve_agent_user(chat_type)
    return prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_support_request_title,
        prompt_library.styles.copywriting_support_request_title,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.personal_dictionary, __get_personal_dictionary(agent_user)),
        (PromptVar.date_and_time, __now()),
    ).render()


def copywriting_support_request_description(
    chat_type: ChatConfigDB.ChatType,
    support_request_type: str,
    content_template: str,
) -> str:
    # add generic components to prepare the composer
    agent_user = resolve_agent_user(chat_type)
    composer = prompt_composer.build(
        prompt_library.contexts.core,
        prompt_library.contexts.copywriting_support_request_description,
        prompt_library.styles.copywriting_support_request_description,
        prompt_library.formats.post_github,
        prompt_library.formats.templated,
        prompt_library.appendices.support_request_type,
        prompt_library.appendices.content_template,
        prompt_library.metas.agent_username,
        prompt_library.metas.agent_website,
        prompt_library.metas.today,
        prompt_library.metas.privacy,
    ).add_variables(
        (PromptVar.agent_name, agent_user.full_name or PLACEHOLDER_NO_DATA),
        (PromptVar.personal_dictionary, __get_personal_dictionary(agent_user)),
        (PromptVar.support_request_type, support_request_type or PLACEHOLDER_NO_DATA),
        (PromptVar.content_template, content_template or PLACEHOLDER_NO_DATA),
        (PromptVar.agent_website, config.website_url),
        (PromptVar.date_and_time, __now()),
    )
    # override and add platform-specific fragments and variables
    match chat_type:
        case ChatConfigDB.ChatType.telegram:
            return (
                composer
                .add_fragments(prompt_library.formats.origin_telegram)
                .add_variables((PromptVar.agent_username, agent_user.telegram_username or PLACEHOLDER_NO_DATA))
            ).render()
    raise ValueError(f"Unsupported chat type: {chat_type}")


def simple_chat_error(error_reason: str) -> str:
    clean_reason = error_reason
    for secret in config.all_secrets():
        clean_reason = clean_reason.replace(secret.get_secret_value(), "****")
    return CHAT_MESSAGE_DELIMITER.join(["🤯", f"```\n{clean_reason}\n```", "Open /settings"])


def __now() -> str:
    return f"{datetime.now().strftime("%A, %B %d %Y")}, {datetime.now().strftime("%I:%M %p")}"


def __get_personal_dictionary(agent_user: UserSave | User) -> str:
    keywords: set[str] = {keyword for keyword in [
        agent_user.full_name, config.parent_organization, config.website_url, config.version,
        agent_user.telegram_username, agent_user.telegram_username,
    ] if keyword}  # eliminates duplicates and None values
    return ", ".join(list(keywords)) or PLACEHOLDER_NO_DATA
