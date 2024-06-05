from chat.telegram.message_entity import MessageEntity


class TextQuote:
    """https://core.telegram.org/bots/api#textquote"""
    text: str
    position: int
    entities: list[MessageEntity] | None

    def __init__(
        self,
        text: str,
        position: int,
        entities: list[MessageEntity] | None = None,
    ):
        self.text = text
        self.position = position
        self.entities = entities
