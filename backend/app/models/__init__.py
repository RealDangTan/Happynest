"""Models package — import module nào là bảng đó đăng ký vào Base.metadata."""

from app.models.analysis_run import AnalysisRun
from app.models.cluster import Cluster
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.llm_call_log import LlmCallLog
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.models.taxonomy import Taxonomy
from app.models.user import User

__all__ = [
    "AnalysisRun",
    "Cluster",
    "Feedback",
    "Import",
    "LlmCallLog",
    "Product",
    "ProductSchema",
    "Taxonomy",
    "User",
]
