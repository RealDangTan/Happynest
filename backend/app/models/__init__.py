"""Models package — import module nào là bảng đó đăng ký vào Base.metadata."""

from app.models.analysis_run import AnalysisRun
from app.models.cluster import Cluster
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.insight import Insight
from app.models.insight_review import InsightReview
from app.models.llm_call_log import LlmCallLog
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.models.taxonomy import Taxonomy
from app.models.user import User

__all__ = [
    "AnalysisRun",
    "Cluster",
    "Evidence",
    "Feedback",
    "Import",
    "Insight",
    "InsightReview",
    "LlmCallLog",
    "Product",
    "ProductSchema",
    "Taxonomy",
    "User",
]
