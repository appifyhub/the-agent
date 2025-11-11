from api.model.connect_key_response import ConnectKeyResponse
from api.model.settings_link_response import SettingsLinkResponse
from db.model.chat_config import ChatConfigDB
from di.di import DI
from features.connect.profile_connect_service import ProfileConnectService
from util import log


class ProfileConnectController:

    __di: DI

    def __init__(self, di: DI):
        self.__di = di

    def get_connect_key(self, user_id_hex: str) -> ConnectKeyResponse:
        log.d(f"Fetching connect key for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        return ConnectKeyResponse(connect_key = user.connect_key)

    def regenerate_connect_key(self, user_id_hex: str) -> ConnectKeyResponse:
        log.d(f"Regenerating connect key for user '{user_id_hex}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)

        new_key = self.__di.profile_connect_service.regenerate_connect_key(user)
        log.i(f"Successfully regenerated connect key for user '{user_id_hex}'")
        return ConnectKeyResponse(connect_key = new_key)

    def connect_profiles(
        self,
        user_id_hex: str,
        target_connect_key: str,
        chat_type: ChatConfigDB.ChatType,
    ) -> SettingsLinkResponse:
        normalized_connect_key = target_connect_key.strip().upper()
        log.d(f"Connecting profiles for user '{user_id_hex}' with target key '{normalized_connect_key}'")
        user = self.__di.authorization_service.authorize_for_user(self.__di.invoker, user_id_hex)
        result, message = self.__di.profile_connect_service.connect_profiles(user, normalized_connect_key)

        if result == ProfileConnectService.Result.failure:
            raise ValueError(message)

        settings_link_response = self.__di.settings_controller.create_settings_link(chat_type = chat_type)
        log.i(f"Successfully connected profiles for user '{user_id_hex}'")
        return settings_link_response
