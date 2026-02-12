"""統一求人スキーマ定義"""

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "docs" / "want.json"

# 統一スキーマのフィールド一覧
FIELDS = [
    "original_id", "access", "access_label", "access_minutes", "address",
    "area", "bonus", "caractoristic", "city", "contract", "dept", "detail",
    "facility_name", "facility_type", "holiday", "license", "line", "name",
    "occupation", "position", "prefecture", "price", "price_rule",
    "required_skill", "staff_comment", "staff_comment_title", "station",
    "test_period", "title_original", "welfare_program", "working_hours",
    "working_style",
]


def empty_record() -> dict:
    """空の統一スキーマレコードを返す"""
    return {f: "" for f in FIELDS}


def normalize(raw: dict, mapping: dict) -> dict:
    """生データをマッピングに従って統一スキーマに変換"""
    record = empty_record()
    for schema_key, source_key in mapping.items():
        if schema_key in record and source_key in raw:
            record[schema_key] = raw[source_key]
    # マッピングにないフィールドも _extra に保存
    mapped_sources = set(mapping.values())
    extra = {k: v for k, v in raw.items() if k not in mapped_sources}
    if extra:
        record["_extra"] = extra
    return record
