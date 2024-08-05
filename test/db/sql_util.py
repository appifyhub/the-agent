from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.chat_message_attachment import ChatMessageAttachmentCRUD
from db.crud.invite import InviteCRUD
from db.crud.user import UserCRUD
from db.sql import BaseModel


class SQLUtil:
    __session: Session
    __is_session_active: bool

    def __init__(self):
        self.__is_session_active = False
        self.start_session()
        self.__is_session_active = True

    def start_session(self) -> Session:
        engine = create_engine("sqlite:///:memory:")
        # noinspection PyPep8Naming
        TestLocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
        BaseModel.metadata.create_all(bind = engine)

        if self.__is_session_active:
            self.end_session()

        self.__session = TestLocalSession()
        self.__is_session_active = True

        return self.__session

    def get_session(self):
        return self.__session

    def end_session(self):
        self.__session.close()
        self.__is_session_active = False

    def chat_config_crud(self) -> ChatConfigCRUD:
        if not self.__is_session_active: self.start_session()
        return ChatConfigCRUD(self.__session)

    def chat_message_crud(self) -> ChatMessageCRUD:
        if not self.__is_session_active: self.start_session()
        return ChatMessageCRUD(self.__session)

    def chat_message_attachment_crud(self) -> ChatMessageAttachmentCRUD:
        if not self.__is_session_active: self.start_session()
        return ChatMessageAttachmentCRUD(self.__session)

    def invite_crud(self) -> InviteCRUD:
        if not self.__is_session_active: self.start_session()
        return InviteCRUD(self.__session)

    def user_crud(self) -> UserCRUD:
        if not self.__is_session_active: self.start_session()
        return UserCRUD(self.__session)
