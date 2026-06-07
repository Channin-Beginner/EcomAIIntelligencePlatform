from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.assistant.schema import AssistantQueryRequest, AssistantQueryResponse
from app.assistant.service import get_suggestions, handle_query
from app.common.response import success
from app.database import get_db

router = APIRouter(prefix="/ops/assistant", tags=["ops-assistant"])


@router.get("/suggestions")
def assistant_suggestions():
    return success(get_suggestions())


@router.post("/query", response_model=None)
def assistant_query(body: AssistantQueryRequest, db: Session = Depends(get_db)):
    result: AssistantQueryResponse = handle_query(db, body.question, body.refDate)
    return success(result.model_dump())
