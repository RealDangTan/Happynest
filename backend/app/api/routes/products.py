"""Routes products — plan 21 (VoC OS: product = workspace, products-only).

CRUD tối thiểu cho phase 21; product switcher FE và schema registry (plan 22)
sẽ dựng trên nền này.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.analysis_run import AnalysisRun
from app.models.decision_log import DecisionLog
from app.models.evidence import Evidence
from app.models.feedback import Feedback
from app.models.import_ import Import
from app.models.insight import Insight
from app.models.llm_call_log import LlmCallLog
from app.models.enums import ImportStatus
from app.models.product import Product
from app.models.product_schema import ProductSchema
from app.models.taxonomy import Taxonomy
from app.schemas.import_ import FieldCoverageOut, ProductSchemaListOut, ProductSchemaOut
from app.schemas.product import ProductIn, ProductListOut, ProductOut, ProductUpdate
from app.services.coverage import field_coverage
from app.services import schema_registry

router = APIRouter(
    prefix="/api/products",
    tags=["products"],
    dependencies=[Depends(require_role("pm", "operations"))],
)

# Destructive ops siết thêm: chỉ pm.
_pm_only = [Depends(require_role("pm"))]

_BUSY_STATUSES = {ImportStatus.mapping_generating, ImportStatus.importing}


@router.get("")
def list_products(
    session: Session = Depends(get_db),
) -> ProductListOut:
    total = session.scalar(select(func.count()).select_from(Product))
    rows = session.scalars(select(Product).order_by(Product.created_at)).all()
    return ProductListOut(
        items=[ProductOut.model_validate(r) for r in rows],
        total=int(total or 0),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product(item: ProductIn, session: Session = Depends(get_db)) -> ProductOut:
    exists = session.scalars(
        select(Product).where(Product.name == item.name)
    ).first()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product '{item.name}' đã tồn tại.",
        )
    product = Product(name=item.name, description=item.description)
    session.add(product)
    session.commit()
    session.refresh(product)
    return ProductOut.model_validate(product)


@router.get("/{product_id}/schema", response_model=None)
def get_active_schema(product_id: uuid.UUID, session: Session = Depends(get_db)):
    """Schema ACTIVE hiện hành (definition + version) — null `schema` khi chưa
    bootstrap (product mới, chưa import CSV nào qua Gate #1)."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    active = schema_registry.get_active_schema(session, product_id)
    return {
        "product_id": product_id,
        "schema": ProductSchemaOut.model_validate(active) if active else None,
        "core_fields": schema_registry.SYSTEM_CORE_FIELDS,
    }


@router.get("/{product_id}/schema/versions")
def list_schema_versions(
    product_id: uuid.UUID, session: Session = Depends(get_db)
) -> ProductSchemaListOut:
    """Toàn bộ version schema của product (mới nhất trước) + version active."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    versions = schema_registry.list_versions(session, product_id)
    active = next((v for v in versions if v.status == "active"), None)
    return ProductSchemaListOut(
        items=[ProductSchemaOut.model_validate(v) for v in versions],
        active_version=active.version if active else None,
    )


@router.get("/{product_id}/schema/coverage")
def get_schema_coverage(
    product_id: uuid.UUID, session: Session = Depends(get_db)
) -> FieldCoverageOut:
    """Coverage per product field từ `data` JSONB (VoC OS §19)."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    from sqlalchemy import text

    total = int(
        session.scalar(
            text("SELECT count(*) FROM feedback WHERE product_id = :pid"),
            {"pid": str(product_id)},
        )
        or 0
    )
    return FieldCoverageOut(
        total_records=total, coverage=field_coverage(session, product_id)
    )


@router.get("/{product_id}")
def get_product(product_id: uuid.UUID, session: Session = Depends(get_db)) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", dependencies=_pm_only)
def update_product(
    product_id: uuid.UUID,
    item: ProductUpdate,
    session: Session = Depends(get_db),
) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    if item.name is not None and item.name != product.name:
        exists = session.scalars(
            select(Product).where(Product.name == item.name)
        ).first()
        if exists is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product '{item.name}' đã tồn tại.",
            )
        product.name = item.name
    if item.description is not None:
        product.description = item.description
    session.commit()
    session.refresh(product)
    return ProductOut.model_validate(product)


@router.delete("/{product_id}", dependencies=_pm_only)
def delete_product(
    product_id: uuid.UUID, session: Session = Depends(get_db)
) -> dict:
    """Hard delete product + TOÀN BỘ dữ liệu con trong 1 transaction (VoC OS:
    product = workspace — xoá workspace là dọn sạch theo cụm). Thứ tự tuân thủ
    FK không-cascade: feedback → evidence → llm_call_logs → insights (con
    cascade DB) → taxonomies → product_schemas → decision_logs → analysis_runs
    → imports → product. 409 khi còn import đang xử lý nền."""
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")

    busy = session.scalar(
        select(func.count())
        .select_from(Import)
        .where(Import.product_id == product_id, Import.status.in_(_BUSY_STATUSES))
    )
    if int(busy or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product còn import đang xử lý — đợi hoàn tất rồi xoá lại.",
        )

    run_ids = select(AnalysisRun.id).where(
        AnalysisRun.import_id.in_(
            select(Import.id).where(Import.product_id == product_id)
        )
    )
    counts: dict[str, int] = {}

    counts["llm_call_logs"] = session.query(LlmCallLog).filter(
        LlmCallLog.analysis_run_id.in_(run_ids)
    ).delete(synchronize_session=False)
    counts["evidence"] = session.query(Evidence).filter(
        Evidence.product_id == product_id
    ).delete(synchronize_session=False)
    counts["feedbacks"] = session.query(Feedback).filter(
        Feedback.product_id == product_id
    ).delete(synchronize_session=False)
    counts["insights"] = session.query(Insight).filter(
        Insight.product_id == product_id
    ).delete(synchronize_session=False)
    counts["taxonomies"] = session.query(Taxonomy).filter(
        Taxonomy.product_id == product_id
    ).delete(synchronize_session=False)
    counts["product_schemas"] = session.query(ProductSchema).filter(
        ProductSchema.product_id == product_id
    ).delete(synchronize_session=False)
    counts["decision_logs"] = session.query(DecisionLog).filter(
        DecisionLog.product_id == product_id
    ).delete(synchronize_session=False)
    counts["analysis_runs"] = session.query(AnalysisRun).filter(
        AnalysisRun.import_id.in_(
            select(Import.id).where(Import.product_id == product_id)
        )
    ).delete(synchronize_session=False)
    counts["imports"] = session.query(Import).filter(
        Import.product_id == product_id
    ).delete(synchronize_session=False)
    session.delete(product)
    session.commit()
    return {"product_id": str(product_id), "deleted_counts": counts}
