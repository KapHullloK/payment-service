from pydantic import BaseModel, ConfigDict, Field


class TariffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ID тарифа.")
    title: str = Field(description="Название тарифа.")
    price: int = Field(description="Цена тарифа в копейках.")
