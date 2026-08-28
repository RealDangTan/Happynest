"""Field coverage — coverage tracking cho dynamic product fields (VoC OS §19).

coverage = records_with_field / relevant_records (mọi row feedback của product).
Agent BẮT BUỘC dùng coverage khi đánh giá evidence quality (phase 24 kèm
coverage vào mọi kết quả aggregate).
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

_COVERAGE_SQL = text("""
    SELECT k AS key, count(*) AS records_with_field
    FROM feedback f,
         LATERAL jsonb_object_keys(f.data) k
    WHERE f.product_id = :pid
    GROUP BY k
""")


def field_coverage(db: Session, product_id: uuid.UUID) -> dict:
    """{field_key: coverage_float} cho mọi key đang có trong `data` JSONB.

    1 query duy nhất (pooler RTT — tránh N query per field). Field có trong
    schema nhưng chưa từng xuất hiện → không nằm trong dict (caller hiểu = 0).
    """
    total = db.execute(
        text("SELECT count(*) FROM feedback WHERE product_id = :pid"),
        {"pid": str(product_id)},
    ).scalar()
    if not total:
        return {}
    rows = db.execute(_COVERAGE_SQL, {"pid": str(product_id)}).mappings()
    return {row["key"]: round(int(row["records_with_field"]) / int(total), 4) for row in rows}
