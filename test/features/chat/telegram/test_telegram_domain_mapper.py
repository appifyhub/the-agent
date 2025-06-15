import unittest
from datetime import datetime

from db.model.user import UserDB
from features.chat.telegram.model.attachment.audio import Audio
from features.chat.telegram.model.attachment.document import Document
from features.chat.telegram.model.attachment.file import File
from features.chat.telegram.model.attachment.photo_size import PhotoSize
from features.chat.telegram.model.attachment.voice import Voice
from features.chat.telegram.model.chat import Chat
from features.chat.telegram.model.message import Message
from features.chat.telegram.model.text_quote import TextQuote
from features.chat.telegram.model.update import Update
from features.chat.telegram.model.user import User
from features.chat.telegram.telegram_domain_mapper import TelegramDomainMapper
from util.config import config


class TelegramDomainMapperTest(unittest.TestCase):
    mapper: TelegramDomainMapper

    def setUp(self):
        config.verbose = True
        self.mapper = TelegramDomainMapper()

    def test_map_update_filled(self):
        update = Update(
            update_id = 1,
            message = Message(
                chat = Chat(id = 10, type = "private"),
                message_id = 100,
                date = int(datetime.now().timestamp()),
                text = "This is a test message",
                **{
                    "from": User(
                        id = 1,
                        first_name = "First",
                        last_name = "Last",
                        username = "username",
                        is_bot = True,
                    ),
                },
                audio = Audio(file_id = "a1", file_unique_id = "a", file_size = 1, mime_type = "audio/mpeg"),
                document = Document(file_id = "d2", file_unique_id = "d", file_size = 2),
            ),
        )

        result = self.mapper.map_update(update)

        self.assertIsNotNone(result)
        self.assertEqual(result.chat.chat_id, "10")
        self.assertEqual(result.message.message_id, "100")
        self.assertEqual(result.message.text, "This is a test message\n\n📎 [ a1 (audio/mpeg), d2 ]")
        self.assertEqual(result.author.full_name, "First Last")
        self.assertEqual(len(result.attachments), 2)
        self.assertEqual(result.attachments[0].id, "a1")
        self.assertEqual(result.attachments[1].id, "d2")

    def test_map_update_empty(self):
        update = Update(update_id = 1)

        result = self.mapper.map_update(update)

        self.assertIsNone(result)

    def test_map_message_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            text = "This is a test message",
            date = int(datetime.now().timestamp()),
            edit_date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_message(message)

        self.assertEqual(result.chat_id, "10")
        self.assertEqual(result.message_id, "100")
        self.assertIsNone(result.author_id)
        self.assertEqual(result.sent_at, datetime.fromtimestamp(message.edit_date))
        self.assertEqual(result.text, "This is a test message")

    def test_map_message_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            caption = "This is a caption",
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_message(message)

        self.assertEqual(result.chat_id, "10")
        self.assertEqual(result.message_id, "100")
        self.assertIsNone(result.author_id)
        self.assertEqual(result.sent_at, datetime.fromtimestamp(message.date))
        self.assertEqual(result.text, "This is a caption")

    def test_map_author_filled(self):
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
            **{
                # stupid Pydantic hack (API name is 'from')
                "from": User(
                    id = 1,
                    first_name = "First",
                    last_name = "Last",
                    username = "username",
                    is_bot = False,
                ),
            },
        )

        result = self.mapper.map_author(message)

        self.assertIsNone(result.id)
        self.assertEqual(result.full_name, "First Last")
        self.assertEqual(result.telegram_username, "username")
        self.assertEqual(result.telegram_chat_id, "10")
        self.assertEqual(result.telegram_user_id, 1)
        self.assertIsNone(result.open_ai_key)
        self.assertEqual(result.group, UserDB.Group.standard)

    def test_map_author_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_author(message)

        self.assertIsNone(result)

    def test_map_text_as_reply_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
            text = "This is a test message",
            caption = "This is a caption",
            audio = Audio(file_id = "a1", file_unique_id = "a", mime_type = "audio/mpeg"),
        )

        result = self.mapper.map_text_as_reply(message)

        expected_text = (
            ">>>> This is a caption\n\n"
            ">>>> This is a test message\n\n"
            ">>>> 📎 [ a1 (audio/mpeg) ]"
        )

        self.assertEqual(result, expected_text)

    def test_map_text_as_reply_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_text_as_reply(message)

        self.assertEqual(result, "")

    def test_map_text_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
            text = "This is a test message",
            caption = "This is a caption",
            reply_to_message = Message(
                chat = Chat(id = 10, type = "private"),
                message_id = 99,
                date = int(datetime.now().timestamp()),
                text = "This is a reply message",
            ),
            quote = TextQuote(text = "This is a quote", position = 0),
            voice = Voice(file_id = "v4", file_unique_id = "v", file_size = 4, mime_type = "audio/ogg"),
        )

        result = self.mapper.map_text(message)

        expected_text = (
            ">>>> This is a reply message\n\n"
            ">> This is a quote\n\n"
            "This is a caption\n\n"
            "This is a test message\n\n"
            "📎 [ v4 (audio/ogg) ]"
        )

        self.assertEqual(result, expected_text)

    def test_map_text_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_text(message)

        self.assertEqual(result, "")

    def test_map_chat_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(
                id = 10,
                type = "private",
                username = "chat_username",
                first_name = "First",
            ),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_chat(message)

        self.assertEqual(result.chat_id, "10")
        self.assertEqual(result.title, "First · @chat_username")
        self.assertIsNone(result.language_iso_code)
        self.assertIsNone(result.language_name)
        self.assertTrue(result.is_private)
        self.assertEqual(result.reply_chance_percent, 100)

    def test_map_chat_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "channel"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )
        message.from_user = User(
            id = 1, is_bot = False, first_name = "F", last_name = "L", username = "U", language_code = "de",
        )

        result = self.mapper.map_chat(message)

        self.assertEqual(result.chat_id, "10")
        self.assertEqual(result.title, "#10")
        self.assertEqual(result.language_iso_code, "de")
        self.assertIsNone(result.language_name)
        self.assertFalse(result.is_private)
        self.assertEqual(result.reply_chance_percent, 100)

    def test_resolve_chat_name_filled(self):
        result = self.mapper.resolve_chat_name(
            chat_id = "10",
            title = "Chat Title",
            username = "chat_username",
            first_name = "First",
            last_name = "Last",
        )

        self.assertEqual(result, "Chat Title · First Last · @chat_username")

    def test_resolve_chat_name_partial(self):
        result = self.mapper.resolve_chat_name(
            chat_id = "10",
            title = "Chat Title",
            username = None,
            first_name = "First",
            last_name = None,
        )

        self.assertEqual(result, "Chat Title · First")

    def test_resolve_chat_name_empty(self):
        result = self.mapper.resolve_chat_name(
            chat_id = "10",
            title = None,
            username = None,
            first_name = None,
            last_name = None,
        )

        self.assertEqual(result, "#10")

    def test_map_attachments_as_text_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            audio = Audio(file_id = "a1", file_unique_id = "a", file_size = 1, mime_type = "audio/mpeg"),
            document = Document(file_id = "d2", file_unique_id = "d", file_size = 2),
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_attachments_as_text(message)

        self.assertEqual(result, "[ a1 (audio/mpeg), d2 ]")

    def test_map_attachments_as_text_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_attachments_as_text(message)

        self.assertIsNone(result)

    def test_map_attachments_filled(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            message_id = 100,
            chat = Chat(id = 10, type = "private"),
            audio = Audio(file_id = "a1", file_unique_id = "a", file_size = 1, mime_type = "audio/mpeg"),
            document = Document(file_id = "d2", file_unique_id = "d", file_size = 2, mime_type = "application/pdf"),
            photo = [
                PhotoSize(file_id = "no", file_unique_id = "no", file_size = 0, width = 1, height = 1),
                PhotoSize(file_id = "p3", file_unique_id = "p", file_size = 3, width = 800, height = 600),
            ],
            voice = Voice(file_id = "v4", file_unique_id = "v", file_size = 4, mime_type = "audio/ogg"),
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_attachments(message)

        self.assertEqual(len(result), 4)
        # audio
        self.assertEqual(result[0].message_id, str(message.message_id))
        self.assertEqual(result[0].id, message.audio.file_id)
        self.assertEqual(result[0].chat_id, str(message.chat.id))
        self.assertEqual(result[0].size, message.audio.file_size)
        self.assertEqual(result[0].mime_type, message.audio.mime_type)
        self.assertIsNone(result[0].extension)
        self.assertIsNone(result[0].last_url)
        self.assertIsNone(result[0].last_url_until)
        # document
        self.assertEqual(result[1].message_id, str(message.message_id))
        self.assertEqual(result[1].id, message.document.file_id)
        self.assertEqual(result[1].chat_id, str(message.chat.id))
        self.assertEqual(result[1].size, message.document.file_size)
        self.assertEqual(result[1].mime_type, message.document.mime_type)
        self.assertIsNone(result[1].extension)
        self.assertIsNone(result[1].last_url)
        self.assertIsNone(result[1].last_url_until)
        # photo
        self.assertEqual(result[2].message_id, str(message.message_id))
        self.assertEqual(result[2].id, message.photo[1].file_id)
        self.assertEqual(result[2].chat_id, str(message.chat.id))
        self.assertEqual(result[2].size, message.photo[1].file_size)
        self.assertIsNone(result[2].mime_type)
        self.assertIsNone(result[2].extension)
        self.assertIsNone(result[2].last_url)
        self.assertIsNone(result[2].last_url_until)
        # voice
        self.assertEqual(result[3].message_id, str(message.message_id))
        self.assertEqual(result[3].id, message.voice.file_id)
        self.assertEqual(result[3].chat_id, str(message.chat.id))
        self.assertEqual(result[3].size, message.voice.file_size)
        self.assertEqual(result[3].mime_type, message.voice.mime_type)
        self.assertIsNone(result[3].extension)
        self.assertIsNone(result[3].last_url)
        self.assertIsNone(result[3].last_url_until)

    def test_map_attachments_empty(self):
        # 'from' is a reserved keyword in Python, so we use a workaround to access it
        # noinspection PyArgumentList
        message = Message(
            chat = Chat(id = 10, type = "private"),
            message_id = 100,
            date = int(datetime.now().timestamp()),
        )

        result = self.mapper.map_attachments(message)

        self.assertEqual(result, [])

    def test_map_to_attachment_filled(self):
        file = File(
            file_id = "123",
            file_unique_id = "ABC",
            file_size = 1024,
            file_path = "path/to/file.png",
        )
        chat_id = "10"
        message_id = "100"
        mime_type = "image/png"

        result = self.mapper.map_to_attachment(file, chat_id, message_id, mime_type)

        self.assertEqual(result.id, file.file_id)
        self.assertEqual(result.chat_id, chat_id)
        self.assertEqual(result.message_id, message_id)
        self.assertEqual(result.size, file.file_size)
        self.assertTrue(result.last_url.endswith(file.file_path))
        self.assertIsNone(result.last_url_until)
        self.assertIsNone(result.extension)
        self.assertEqual(result.mime_type, mime_type)

    def test_map_to_attachment_filled_no_mime_type(self):
        file = File(
            file_id = "123",
            file_unique_id = "ABC",
            file_size = 1024,
            file_path = "path/to/file.png",
        )
        chat_id = "10"
        message_id = "100"

        result = self.mapper.map_to_attachment(file, chat_id, message_id, mime_type = None)

        self.assertEqual(result.id, file.file_id)
        self.assertEqual(result.chat_id, chat_id)
        self.assertEqual(result.message_id, message_id)
        self.assertEqual(result.size, file.file_size)
        self.assertTrue(result.last_url.endswith(file.file_path))
        self.assertIsNone(result.last_url_until)
        self.assertIsNone(result.extension)
        self.assertIsNone(result.mime_type)

    def test_map_to_attachment_empty(self):
        file = File(
            file_id = "123",
            file_unique_id = "ABC",
        )
        chat_id = "10"
        message_id = "100"

        result = self.mapper.map_to_attachment(file, chat_id, message_id, mime_type = None)

        self.assertEqual(result.id, file.file_id)
        self.assertEqual(result.chat_id, chat_id)
        self.assertEqual(result.message_id, message_id)
        self.assertEqual(result.size, file.file_size)
        self.assertIsNone(result.last_url)
        self.assertIsNone(result.last_url_until)
        self.assertIsNone(result.extension)
        self.assertIsNone(result.mime_type)
