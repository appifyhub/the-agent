from pydantic import BaseModel


class Contact(BaseModel):
    input: str
    wa_id: str


class Message(BaseModel):
    id: str
    message_status: str | None = None


class MessageResponse(BaseModel):
    messaging_product: str
    contacts: list[Contact]
    messages: list[Message]


class MediaUploadResponse(BaseModel):
    id: str


class ErrorResponse(BaseModel):
    error: dict


class MarkAsReadResponse(BaseModel):
    success: bool


class ApiResponse(BaseModel):
    status: str | None = None
    message: str | None = None
    data: MessageResponse | MediaUploadResponse | None = None
    error: dict | None = None
