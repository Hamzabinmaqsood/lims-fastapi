"""Read a growth-stage spreadsheet (.xlsx or .csv) into validated StageIn objects."""

import csv
import io

from openpyxl import load_workbook
from pydantic import ValidationError

from app.modules.growth_stages.models import INDEX_NAMES
from app.modules.growth_stages.schemas import StageIn

# Old spreadsheets call RECI "RECL".
ALIASES = {"reci": ["reci", "recl"]}


def read_rows(content: bytes, filename: str) -> list[dict[str, str]]:
    """Return one dict per data row, keyed by lower-case header names."""
    name = filename.lower()

    if name.endswith(".csv"):
        text = content.decode("utf-8-sig")  # utf-8-sig drops Excel's hidden BOM character
        return [
            {_header(k): (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(io.StringIO(text))
            if any((v or "").strip() for v in row.values())  # skip blank lines
        ]

    if name.endswith(".xlsx"):
        sheet = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        rows = sheet.iter_rows(values_only=True)
        header = [_header(h) for h in next(rows, [])]
        result = []
        for values in rows:
            if all(v in (None, "") for v in values):
                continue  # skip blank rows
            row = {}
            for h, v in zip(header, values):
                if not h:
                    continue
                if isinstance(v, float):
                    v = round(v, 3)  # Excel floats like 0.35000000000000003
                row[h] = "" if v is None else str(v).strip()
            result.append(row)
        return result

    raise ValueError("Only .xlsx or .csv files are supported.")


def parse_days(text: str) -> tuple[int, int]:
    """'0-15', '0 – 15' or '0 to 15'  →  (0, 15)."""
    cleaned = text.replace("–", "-").replace("—", "-").lower().replace("to", "-")
    parts = [p.strip() for p in cleaned.split("-") if p.strip()]
    if len(parts) != 2:
        raise ValueError(f"Interval Days must look like 0-15 (got '{text}').")
    return int(float(parts[0])), int(float(parts[1]))


def _cell(row: dict[str, str], index: str, kind: str) -> str:
    for prefix in ALIASES.get(index.lower(), [index.lower()]):
        value = row.get(f"{prefix} {kind}", "")
        if value:
            return value
    return ""


def build_stages(rows: list[dict[str, str]], crop_id: int) -> tuple[list[StageIn], list[dict]]:
    stages: list[StageIn] = []
    errors: list[dict] = []

    for row_number, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            day_from, day_to = parse_days(row.get("interval days", ""))
            ranges = []
            for index in INDEX_NAMES:
                low, high = _cell(row, index, "low"), _cell(row, index, "high")
                if not low and not high:
                    continue  # this index isn't used for this stage
                ranges.append({
                    "index_name": index,
                    "low": low,
                    "high": high,
                    "title": _cell(row, index, "title") or None,
                    "description": _cell(row, index, "description") or None,
                })
            stages.append(StageIn(
                crop_id=crop_id, name=row.get("growth stage", ""),
                day_from=day_from, day_to=day_to, ranges=ranges,
            ))
        except ValidationError as exc:  # must come BEFORE ValueError (it's a subclass)
            errors.append({
                "row": row_number,
                "errors": [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()],
            })
        except ValueError as exc:
            errors.append({"row": row_number, "errors": [str(exc)]})

    # Rows must not overlap each other either.
    ordered = sorted(stages, key=lambda s: s.day_from)
    for a, b in zip(ordered, ordered[1:]):
        if b.day_from <= a.day_to:
            errors.append({"row": None, "errors": [
                f"'{a.name}' ({a.day_from}-{a.day_to}) overlaps '{b.name}' ({b.day_from}-{b.day_to})."
            ]})
    return stages, errors

def _header(name) -> str:
    """'SAVI_LOW', 'savi low', ' Savi  Low ' → 'savi low'."""
    return " ".join(str(name or "").replace("_", " ").split()).lower()
