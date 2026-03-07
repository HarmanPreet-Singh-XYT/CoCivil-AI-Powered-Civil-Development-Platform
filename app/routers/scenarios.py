import hashlib
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db_session
from app.models.tenant import ScenarioRun
from app.schemas.tenant import ScenarioCreate, ScenarioResponse

router = APIRouter()


@router.post("/projects/{project_id}/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    project_id: uuid.UUID,
    body: ScenarioCreate,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    input_hash = hashlib.sha256(
        json.dumps(body.model_dump(), sort_keys=True, default=str).encode()
    ).hexdigest()
    scenario = ScenarioRun(
        project_id=project_id,
        parent_scenario_id=body.parent_scenario_id,
        scenario_type=body.scenario_type,
        input_hash=input_hash,
        snapshot_manifest_id=body.snapshot_manifest_id,
        status="pending",
    )
    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)
    return scenario


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    result = await db.execute(select(ScenarioRun).where(ScenarioRun.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.get("/scenarios/{scenario_id}/compare/{other_id}")
async def compare_scenarios(
    scenario_id: uuid.UUID,
    other_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    # TODO: Implement scenario comparison logic
    return {
        "scenario_a": str(scenario_id),
        "scenario_b": str(other_id),
        "deltas": {},
    }
