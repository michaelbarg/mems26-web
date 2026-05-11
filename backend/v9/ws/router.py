"""V9 Event Bus WebSocket router — aggregates all WS endpoints from the Event Bus."""

from fastapi import APIRouter

from .price_channel import router as price_router

router = APIRouter()
router.include_router(price_router)
