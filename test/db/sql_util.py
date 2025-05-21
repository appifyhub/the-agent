from sqlalchemy.orm import Session

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.price_alert import PriceAlertCRUD
from db.crud.sponsorship import SponsorshipCRUD
from db.crud.tools_cache import ToolsCacheCRUD
from db.crud.user import UserCRUD
from db.sql import initialize_db


class SQLUtil:
    __session: Session
    __is_session_active: bool

    def __init__(self):
        self.__is_session_active = False
        self.start_session()
        self.__is_session_active = True

    def start_session(self) -> Session:
        # noinspection PyPep8Naming
        engine, LocalSession = initialize_db("sqlite:///:memory:", multi_connection_setup = False)

        if self.__is_session_active:
            self.end_session()

        self.__session = LocalSession()
        self.__is_session_active = True

        return self.__session

    def get_session(self):
        return self.__session

    def end_session(self):
        self.__session.close()
        self.__is_session_active = False

    def chat_config_crud(self) -> ChatConfigCRUD:
        if not self.__is_session_active:
            self.start_session()
        return ChatConfigCRUD(self.__session)

    def chat_message_crud(self) -> ChatMessageCRUD:
        if not self.__is_session_active:
            self.start_session()
        return ChatMessageCRUD(self.__session)

    def chat_message_attachment_crud(self) -> ChatMessageAttachmentCRUD:
        if not self.__is_session_active:
            self.start_session()
        return ChatMessageAttachmentCRUD(self.__session)

    def sponsorship_crud(self) -> SponsorshipCRUD:
        if not self.__is_session_active:
            self.start_session()
        return SponsorshipCRUD(self.__session)

    def tools_cache_crud(self) -> ToolsCacheCRUD:
        if not self.__is_session_active:
            self.start_session()
        return ToolsCacheCRUD(self.__session)

    def user_crud(self) -> UserCRUD:
        if not self.__is_session_active:
            self.start_session()
        return UserCRUD(self.__session)

    def price_alert_crud(self) -> PriceAlertCRUD:
        if not self.__is_session_active:
            self.start_session()
        return PriceAlertCRUD(self.__session)
