from __future__ import annotations

from fastapi import APIRouter, Depends

from data_analyst_agent.api.schema.dataset.dataset import DatasetSchemaResponse
from data_analyst_agent.auth.dependencies import get_current_user
from data_analyst_agent.services.data_factory import get_data_source_provider

router = APIRouter()


@router.get(
    "/dataset/schema",
    response_model=DatasetSchemaResponse,
    dependencies=[Depends(get_current_user)],
)
async def dataset_schema() -> DatasetSchemaResponse:
    schema = get_data_source_provider().get_schema()
    return DatasetSchemaResponse(**schema)
