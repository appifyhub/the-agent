from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.crud.chat_config import ChatConfigCRUD
from db.crud.chat_message import ChatMessageCRUD
from db.crud.invite import InviteCRUD
from db.crud.user import UserCRUD
from db.sql import BaseModel


class SQLUtil:
    _session: Session
    _is_session_active: bool = False

    def __init__(self):
        self.start_session()
        self._is_session_active = True

    def start_session(self) -> Session:
        engine = create_engine("sqlite:///:memory:")
        # noinspection PyPep8Naming
        TestLocalSession = sessionmaker(autocommit = False, autoflush = False, bind = engine)
        BaseModel.metadata.create_all(bind = engine)

        if self._is_session_active:
            self.end_session()

        self._session = TestLocalSession()
        self._is_session_active = True

        return self._session

    def get_session(self):
        return self._session

    def end_session(self):
        self._session.close()
        self._is_session_active = False

    def chat_config_crud(self) -> ChatConfigCRUD:
        if not self._is_session_active: self.start_session()
        return ChatConfigCRUD(self._session)

    def chat_message_crud(self) -> ChatMessageCRUD:
        if not self._is_session_active: self.start_session()
        return ChatMessageCRUD(self._session)

    def invite_crud(self) -> InviteCRUD:
        if not self._is_session_active: self.start_session()
        return InviteCRUD(self._session)

    def user_crud(self) -> UserCRUD:
        if not self._is_session_active: self.start_session()
        return UserCRUD(self._session)
