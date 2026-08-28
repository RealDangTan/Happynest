"""Routes products — plan 21 (VoC OS: product = workspace, products-only).

CRUD tối thiểu cho phase 21; product switcher FE và schema registry (plan 22)
sẽ dựng trên nền này.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.product import Product
from app.schemas.product import ProductIn, ProductListOut, ProductOut, ProductUpdate

router = APIRouter(
    prefix="/api/products",
    tags=["products"],
    dependencies=[Depends(require_role("pm", "operations"))],
)


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


@router.get("/{product_id}")
def get_product(product_id: uuid.UUID, session: Session = Depends(get_db)) -> ProductOut:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product không tồn tại.")
    return ProductOut.model_validate(product)


@router.patch("/{product_id}")
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
