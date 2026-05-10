from fastapi import APIRouter
from api.v1.personas import router as personas_router
from api.v1.tools import router as tools_router
from api.v1.chat import router as chat_router

router = APIRouter(prefix="/v1")
router.include_router(personas_router)
router.include_router(tools_router)
router.include_router(chat_router)
