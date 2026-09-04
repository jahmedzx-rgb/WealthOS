from app.api.v1.accounting import (
    router as accounting_router,
)
from fastapi import APIRouter

from app.api.v1.investing import router as investing_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.document_imports import router as document_imports_router
from app.api.v1.account import router as account_router
from app.api.v1.auth import router as auth_router


api_router = APIRouter(
    prefix="/api/v1",
    tags=["API v1"],
)

api_router.include_router(investing_router)
api_router.include_router(accounting_router)
api_router.include_router(portfolio_router)
api_router.include_router(document_imports_router)
api_router.include_router(account_router)
api_router.include_router(auth_router)
