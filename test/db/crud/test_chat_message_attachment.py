import unittest

from db.schema.chat_message import ChatMessageSave
from db.schema.chat_message_attachment import ChatMessageAttachmentSave
from db.sql_util import SQLUtil


class TestChatMessageAttachmentCRUD(unittest.TestCase):
    sql: SQLUtil

    def setUp(self):
        self.sql = SQLUtil()

    def tearDown(self):
        self.sql.end_session()

    def test_create_attachment(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, world!",
            )
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "attach1",
            chat_id = chat_message.chat_id,
            message_id = chat_message.message_id,
            size = 1024,
            last_url = "https://example.com/attachment",
            last_url_until = 1234567890,
            extension = "jpg",
            mime_type = "image/jpeg",
        )

        attachment = self.sql.chat_message_attachment_crud().create(attachment_data)

        self.assertEqual(attachment.id, attachment_data.id)
        self.assertEqual(attachment.chat_id, attachment_data.chat_id)
        self.assertEqual(attachment.message_id, attachment_data.message_id)
        self.assertEqual(attachment.size, attachment_data.size)
        self.assertEqual(attachment.last_url, attachment_data.last_url)
        self.assertEqual(attachment.last_url_until, attachment_data.last_url_until)
        self.assertEqual(attachment.extension, attachment_data.extension)
        self.assertEqual(attachment.mime_type, attachment_data.mime_type)

    def test_get_attachment(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, world!",
            )
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "attach1",
            chat_id = chat_message.chat_id,
            message_id = chat_message.message_id,
        )
        created_attachment = self.sql.chat_message_attachment_crud().create(attachment_data)

        fetched_attachment = self.sql.chat_message_attachment_crud().get("attach1")

        self.assertEqual(fetched_attachment.id, created_attachment.id)
        self.assertEqual(fetched_attachment.chat_id, created_attachment.chat_id)
        self.assertEqual(fetched_attachment.message_id, created_attachment.message_id)

    def test_get_all_attachments(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, world!",
            )
        )
        attachments = [
            self.sql.chat_message_attachment_crud().create(
                ChatMessageAttachmentSave(
                    id = "attach1",
                    chat_id = chat_message.chat_id,
                    message_id = chat_message.message_id,
                )
            ),
            self.sql.chat_message_attachment_crud().create(
                ChatMessageAttachmentSave(
                    id = "attach2",
                    chat_id = chat_message.chat_id,
                    message_id = chat_message.message_id,
                )
            ),
        ]

        fetched_attachments = self.sql.chat_message_attachment_crud().get_all()

        self.assertEqual(len(fetched_attachments), len(attachments))
        for i in range(len(attachments)):
            self.assertEqual(fetched_attachments[i].id, attachments[i].id)
            self.assertEqual(fetched_attachments[i].chat_id, attachments[i].chat_id)
            self.assertEqual(fetched_attachments[i].message_id, attachments[i].message_id)

    def test_update_attachment(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, World!",
            )
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "att1",
            chat_id = chat_message.chat_id,
            message_id = chat_message.message_id,
        )
        created_attachment = self.sql.chat_message_attachment_crud().create(attachment_data)

        update_data = ChatMessageAttachmentSave(
            id = created_attachment.id,
            chat_id = created_attachment.chat_id,
            message_id = created_attachment.message_id,
            size = 2048,
            last_url = "https://example.com/newfile",
            last_url_until = 9876543210,
            extension = "png",
            mime_type = "image/png",
        )
        updated_attachment = self.sql.chat_message_attachment_crud().update(update_data)

        self.assertEqual(updated_attachment.id, created_attachment.id)
        self.assertEqual(updated_attachment.chat_id, created_attachment.chat_id)
        self.assertEqual(updated_attachment.message_id, created_attachment.message_id)
        self.assertEqual(updated_attachment.size, update_data.size)
        self.assertEqual(updated_attachment.last_url, update_data.last_url)
        self.assertEqual(updated_attachment.last_url_until, update_data.last_url_until)
        self.assertEqual(updated_attachment.extension, update_data.extension)
        self.assertEqual(updated_attachment.mime_type, update_data.mime_type)

    def test_save_attachment(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, world!",
            )
        )

        attachment_data = ChatMessageAttachmentSave(
            id = "attach1",
            chat_id = chat_message.chat_id,
            message_id = chat_message.message_id,
            size = 1024,
            last_url = "https://example.com/attachment",
            last_url_until = 1234567890,
            extension = "jpg",
            mime_type = "image/jpeg",
        )

        # First, save should create the record
        saved_attachment = self.sql.chat_message_attachment_crud().save(attachment_data)
        self.assertIsNotNone(saved_attachment)
        self.assertEqual(saved_attachment.id, attachment_data.id)
        self.assertEqual(saved_attachment.chat_id, attachment_data.chat_id)
        self.assertEqual(saved_attachment.message_id, attachment_data.message_id)
        self.assertEqual(saved_attachment.size, attachment_data.size)
        self.assertEqual(saved_attachment.last_url, attachment_data.last_url)
        self.assertEqual(saved_attachment.last_url_until, attachment_data.last_url_until)
        self.assertEqual(saved_attachment.extension, attachment_data.extension)
        self.assertEqual(saved_attachment.mime_type, attachment_data.mime_type)

        # Now, save should update the existing record
        update_data = ChatMessageAttachmentSave(
            id = attachment_data.id,
            chat_id = attachment_data.chat_id,
            message_id = attachment_data.message_id,
            last_url = "https://example.com/newfile",
        )
        updated_attachment = self.sql.chat_message_attachment_crud().save(update_data)
        self.assertIsNotNone(updated_attachment)
        self.assertEqual(updated_attachment.id, attachment_data.id)
        self.assertEqual(updated_attachment.chat_id, attachment_data.chat_id)
        self.assertEqual(updated_attachment.message_id, attachment_data.message_id)
        self.assertEqual(updated_attachment.size, update_data.size)
        self.assertEqual(updated_attachment.last_url, update_data.last_url)
        self.assertEqual(updated_attachment.last_url_until, update_data.last_url_until)
        self.assertEqual(updated_attachment.extension, update_data.extension)
        self.assertEqual(updated_attachment.mime_type, update_data.mime_type)

    def test_delete_attachment(self):
        chat_message = self.sql.chat_message_crud().create(
            ChatMessageSave(
                chat_id = "chat1",
                message_id = "msg1",
                text = "Hello, World!",
            )
        )
        attachment_data = ChatMessageAttachmentSave(
            id = "att1",
            chat_id = chat_message.chat_id,
            message_id = chat_message.message_id,
        )
        created_attachment = self.sql.chat_message_attachment_crud().create(attachment_data)

        deleted_attachment = self.sql.chat_message_attachment_crud().delete(created_attachment.id)

        self.assertEqual(deleted_attachment.id, created_attachment.id)
        self.assertEqual(deleted_attachment.chat_id, created_attachment.chat_id)
        self.assertEqual(deleted_attachment.message_id, created_attachment.message_id)
        self.assertIsNone(self.sql.chat_message_attachment_crud().get(created_attachment.id))
