from sqlalchemy import Boolean, Column, ForeignKeyConstraint, Index, PrimaryKeyConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from db.model.base import BaseModel


class ChatMembershipDB(BaseModel):
    __tablename__ = "chat_memberships"

    user_id = Column(UUID(as_uuid = True), nullable = False)
    chat_id = Column(UUID(as_uuid = True), nullable = False)
    is_admin = Column(Boolean, nullable = False, default = False, server_default = text("false"))

    use_about_me = Column(Boolean, nullable = False, default = True, server_default = text("true"))
    use_custom_prompt = Column(Boolean, nullable = False, default = True, server_default = text("true"))

    __table_args__ = (
        PrimaryKeyConstraint(user_id, chat_id, name = "pk_chat_membership"),
        ForeignKeyConstraint([user_id], ["simulants.id"], name = "chat_memberships_user_id_fkey"),
        ForeignKeyConstraint([chat_id], ["chat_configs.chat_id"], name = "chat_memberships_chat_id_fkey"),
        Index("ix_chat_memberships_user_id", user_id),
        Index("ix_chat_memberships_chat_id", chat_id),
    )
