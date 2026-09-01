from app.handlers.common import router as common_router
from app.handlers.preview_edit import router as preview_edit_router
from app.handlers.publishing import router as publishing_router
from app.handlers.quick_create import router as quick_create_router
from app.handlers.quiz_engine import router as quiz_engine_router
from app.handlers.quiz_start import router as quiz_start_router
from app.handlers.results import router as results_router

__all__ = [
    "common_router",
    "quick_create_router",
    "preview_edit_router",
    "publishing_router",
    "quiz_start_router",
    "quiz_engine_router",
    "results_router",
]
