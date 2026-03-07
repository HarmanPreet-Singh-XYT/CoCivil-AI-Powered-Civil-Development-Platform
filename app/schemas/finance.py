import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.services.thin_slice_runtime import FinancialAssumptionPayload


class FinancialRunRequest(BaseModel):
    assumption_set_id: uuid.UUID | None = None
    parameters: dict[str, Any] | None = None


class FinancialAssumptionSetReferenceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None = None
    name: str
    is_default: bool
    assumptions_json: FinancialAssumptionPayload
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialOutputResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    tenure: str | None = None
    total_revenue: float | None = None
    hard_cost: float | None = None
    soft_cost: float | None = None
    contingency_cost: float | None = None
    total_cost: float | None = None
    opex: float | None = None
    noi: float | None = None
    valuation: float | None = None
    residual_land_value: float | None = None
    assumptions_used: FinancialAssumptionPayload | dict[str, Any] | None = None


class FinancialRunResponse(BaseModel):
    id: uuid.UUID
    scenario_run_id: uuid.UUID
    assumption_set_id: uuid.UUID | None = None
    layout_run_id: uuid.UUID | None = None
    status: str
    total_revenue: float | None = None
    total_cost: float | None = None
    noi: float | None = None
    valuation: float | None = None
    residual_land_value: float | None = None
    irr_pct: float | None = None
    output_json: FinancialOutputResponse | dict[str, Any] | None = None
    assumption_set: FinancialAssumptionSetReferenceResponse | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
