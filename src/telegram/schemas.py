from pydantic import BaseModel, ConfigDict, Field


class ChatTelegram(BaseModel):
    id: int
    tipo: str = Field(alias="type")

    model_config = ConfigDict(populate_by_name=True)


class MensajeTelegram(BaseModel):
    message_id: int
    chat: ChatTelegram
    texto: str | None = Field(default=None, alias="text")

    model_config = ConfigDict(populate_by_name=True)


class ActualizacionTelegram(BaseModel):
    update_id: int
    message: MensajeTelegram | None = None
