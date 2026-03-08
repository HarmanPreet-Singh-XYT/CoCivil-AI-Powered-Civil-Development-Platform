from typing import Literal

from pydantic import BaseModel, Field


class AssistantChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class UploadContextItem(BaseModel):
    filename: str
    doc_category: str | None = None
    summary: str | None = None
    extracted_data: dict | None = None


class AssistantChatRequest(BaseModel):
    messages: list[AssistantChatMessage] = Field(min_length=1, max_length=20)
    parcel_context: str | None = Field(default=None, max_length=2000)
    model_params: dict | None = None
    zone_code: str | None = None
    upload_context: list[UploadContextItem] | None = None


class ProposedAction(BaseModel):
    label: str
    query: str
    doc_types: list[str] | str | None = None


class ModelUpdate(BaseModel):
    storeys: int
    podium_storeys: int
    height_m: float
    setback_m: float
    typology: str
    footprint_coverage: float
    unit_width: float | None = None
    tower_shape: str | None = None
    warnings: list[str] | None = None


class ContractorRecommendation(BaseModel):
    name: str
    rating: float | None = None
    review_count: int | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    trade: str | None = None


class AssistantChatResponse(BaseModel):
    message: str
    proposed_action: ProposedAction | None = None
    model_update: ModelUpdate | None = None
    contractors: list[ContractorRecommendation] | None = None


class ModelParseRequest(BaseModel):
    text: str
    current_params: dict | None = None
    zone_code: str | None = None
    lot_area_m2: float | None = None


class ModelParseResponse(BaseModel):
    storeys: int
    podium_storeys: int
    height_m: float
    setback_m: float
    typology: str
    footprint_coverage: float
    unit_width: float | None = None
    tower_shape: str | None = None
    warnings: list[str] | None = None


class InfraModelUpdate(BaseModel):
    pipe_type: str | None = None
    material: str | None = None
    diameter_mm: float | None = None
    depth_m: float | None = None
    slope_pct: float | None = None
    bridge_type: str | None = None
    structure_type: str | None = None
    span_m: float | None = None
    deck_width_m: float | None = None
    clearance_m: float | None = None
    warnings: list[str] | None = None


class InfraModelParseRequest(BaseModel):
    text: str
    asset_type: Literal["pipeline", "bridge"]
    current_params: dict | None = None


class InfraModelParseResponse(BaseModel):
    asset_type: str
    params: dict
    warnings: list[str] | None = None
