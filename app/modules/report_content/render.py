"""Fill {placeholders} in admin-editable templates — safely."""

import re

_PLACEHOLDER = re.compile(r"\{(\w+)\}")  # only {plain_names}, nothing else


def render(template: str, values: dict[str, str]) -> str:
    """Replace known {name}s; leave unknown ones as they are."""
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def pct(value: float) -> str:
    return f"{value:.1f} فیصد"  # "62.5 فیصد" (Urdu for "percent")


def attach_texts(indices: list[dict], paragraphs: dict, guidance: dict) -> list[dict]:
    """Add the approved paragraph (by dominant colour) and guidance to each index result."""
    for item in indices:
        zones = item.get("zones") or {}
        color = item.get("dominant_color")
        values = {
            "index_name": item["index"],
            "red_percentage": pct(zones.get("RED", 0)),
            "yellow_percentage": pct(zones.get("YELLOW", 0)),
            "light_green_percentage": pct(zones.get("LIGHT_GREEN", 0)),
            "green_percentage": pct(zones.get("GREEN", 0)),
        }
        template = paragraphs.get((item["index"], color))
        item["paragraph"] = (
            render(template, values) if template
            else render("{index_name} کے لیے ڈیٹا دستیاب نہیں ہے۔", values)  # "no data for ..."
        )
        g = guidance.get(item["index"])
        # Django rule: show guidance only when more than half the farm is red.
        item["guidance"] = (
            {"special_instructions": g.special_instructions, "practical_actions": g.practical_actions}
            if g and zones.get("RED", 0) > 50 else None
        )
    return indices
