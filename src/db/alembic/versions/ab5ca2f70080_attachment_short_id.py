"""attachment_short_id

Revision ID: ab5ca2f70080
Revises: 286e96152dc5
Create Date: 2025-07-20 19:29:07.116749

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "ab5ca2f70080"
down_revision: Union[str, None] = "286e96152dc5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the ext_id column
    op.add_column("chat_message_attachments", sa.Column("ext_id", sa.String(), nullable = True))

    # 2. Migrate existing data: move current id to ext_id and generate new short UUIDs
    connection = op.get_bind()

    # Get all existing attachments
    result = connection.execute(text("SELECT id FROM chat_message_attachments"))
    attachments = result.fetchall()

    # For each attachment, move old id to ext_id and generate new short UUID
    for attachment in attachments:
        old_id = attachment.id
        new_short_id = uuid.uuid4().hex[:8]

        # Update the record
        connection.execute(
            text("UPDATE chat_message_attachments SET ext_id = :old_id, id = :new_id WHERE id = :old_id"),
            {"old_id": old_id, "new_id": new_short_id},
        )


def downgrade() -> None:
    # Restore original data: move ext_id back to id
    connection = op.get_bind()

    # Get all attachments with ext_id
    result = connection.execute(text("SELECT id, ext_id FROM chat_message_attachments WHERE ext_id IS NOT NULL"))
    attachments = result.fetchall()

    # Restore original ids
    for attachment in attachments:
        connection.execute(
            text("UPDATE chat_message_attachments SET id = :ext_id WHERE id = :current_id"),
            {"ext_id": attachment.ext_id, "current_id": attachment.id},
        )

    # Drop the ext_id column
    op.drop_column("chat_message_attachments", "ext_id")
