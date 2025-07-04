import os
from enum import Enum

import requests
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from api.authorization_service import AuthorizationService
from db.crud.chat_config import ChatConfigCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.user import UserCRUD
from db.schema.user import User
from features.chat.telegram.sdk.telegram_bot_sdk import TelegramBotSDK
from features.external_tools.access_token_resolver import AccessTokenResolver
from features.external_tools.external_tool_library import CLAUDE_4_SONNET
from features.prompting import prompt_library
from util.config import config
from util.safe_printer_mixin import SafePrinterMixin

GITHUB_BASE_URL = "https://api.github.com"


class UserSupportManager(SafePrinterMixin):
    class RequestType(Enum):
        bug = "bug_report"
        request = "request_support"
        feature = "feature_request"

    __user_input: str
    __invoker_github_username: str | None
    __include_telegram_username: bool
    __include_full_name: bool
    __request_type: RequestType
    __invoker_user: User
    __user_dao: UserCRUD
    __telegram_bot_sdk: TelegramBotSDK
    __copywriter: BaseChatModel
    __token_resolver: AccessTokenResolver

    def __init__(
        self,
        user_input: str,
        invoker_user_id_hex: str,
        invoker_github_username: str | None,
        include_telegram_username: bool,
        include_full_name: bool,
        request_type_str: str | None,
        user_dao: UserCRUD,
        chat_config_dao: ChatConfigCRUD,
        sponsorship_dao: SponsorshipCRUD,
        telegram_bot_sdk: TelegramBotSDK,
    ):
        super().__init__(config.verbose)
        self.__user_input = user_input
        self.__invoker_github_username = invoker_github_username
        self.__include_telegram_username = include_telegram_username
        self.__include_full_name = include_full_name
        self.__request_type = self.__resolve_request_type(request_type_str)
        self.__user_dao = user_dao
        self.__telegram_bot_sdk = telegram_bot_sdk

        authorization_service = AuthorizationService(telegram_bot_sdk, user_dao, chat_config_dao)
        self.__invoker_user = authorization_service.validate_user(invoker_user_id_hex)
        self.__token_resolver = AccessTokenResolver(
            invoker_user = self.__invoker_user,
            user_dao = user_dao,
            sponsorship_dao = sponsorship_dao,
        )
        anthropic_token = self.__token_resolver.require_access_token_for_tool(CLAUDE_4_SONNET)

        # noinspection PyArgumentList
        self.__copywriter = ChatAnthropic(
            model_name = CLAUDE_4_SONNET.id,
            temperature = 0.5,
            max_tokens = 700,
            timeout = float(config.web_timeout_s),
            max_retries = config.web_retries,
            api_key = anthropic_token,
        )

    def __resolve_request_type(self, request_type_str: str | None) -> RequestType:
        request_type_str = request_type_str.lower() if request_type_str else None
        self.sprint(f"Resolving request type: '{request_type_str}'")
        for request_type in self.RequestType:
            if request_type.name == request_type_str:
                return request_type
        default = UserSupportManager.RequestType.request
        self.sprint(f"Request type not found, defaulting to {default}")
        return default

    def __load_template(self) -> str:
        self.sprint(f"Loading issue template for: {self.__request_type.value}")
        path = os.path.join(config.issue_templates_abs_path, f"{self.__request_type.value}.yaml")
        with open(path, "r") as file:
            return file.read()

    def __generate_issue_description(self) -> str:
        self.sprint("Generating issue description")
        template_contents = self.__load_template()
        prompt = prompt_library.support_request_generator(self.__request_type.name, template_contents)
        user_info_parts = []
        if self.__include_telegram_username and self.__invoker_user.telegram_username:
            user_link = f"[{self.__invoker_user.telegram_username}](https://t.me/{self.__invoker_user.telegram_username})"
            user_info_parts.append(f"Telegram user: {user_link}")
        if self.__invoker_github_username:
            user_info_parts.append(f"GitHub username: @{self.__invoker_github_username}")
        if self.__include_full_name and self.__invoker_user.full_name:
            user_info_parts.append(f"Full name: {self.__invoker_user.full_name}")
        if not user_info_parts:
            user_info_parts.append(f"User ID: T-{self.__invoker_user.id.hex}")
        user_info = "\n".join(user_info_parts)
        message = f"Reporter:\n{user_info}\n\nRaw reporter input:\n```\n{self.__user_input}\n```\n"
        response = self.__copywriter.invoke([SystemMessage(prompt), HumanMessage(message)])
        if not isinstance(response, AIMessage):
            raise AssertionError(f"Received a non-AI message from LLM: {response}")
        return str(response.content)

    def __generate_issue_title(self, description: str) -> str:
        self.sprint("Generating issue title")
        prompt = prompt_library.support_request_title_generator
        message = f"Issue description:\n```\n{description}\n```\n\nIssue type: '{self.__request_type.name}'"
        response = self.__copywriter.invoke([SystemMessage(prompt), HumanMessage(message)])
        if not isinstance(response, AIMessage):
            raise AssertionError(f"Received a non-AI message from LLM: {response}")
        return str(response.content)

    def execute(self) -> str:
        self.sprint("Creating user support request / issue")

        issue_description = self.__generate_issue_description()
        issue_title = self.__generate_issue_title(issue_description)
        github_token = config.github_issues_token.get_secret_value()
        response = requests.post(
            f"{GITHUB_BASE_URL}/repos/{config.github_issues_repo}/issues",
            json = {
                "title": issue_title,
                "body": issue_description,
                "labels": [self.__request_type.name.capitalize()],
            },
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout = float(config.web_timeout_s),
        )
        response.raise_for_status()

        issue = response.json()
        issue_url = str(issue["html_url"])
        self.sprint(f"Issue created successfully. Issue URL: {issue_url}")
        return issue_url
