"""Compare satellite index values with a growth stage's healthy ranges."""


def assess(values: dict[str, float], ranges: list) -> list[dict]:
    by_index = {r.index_name: r for r in ranges}
    result = []
    for name, value in values.items():
        r = by_index.get(name)
        if r is None:
            result.append({"index": name, "value": value, "low": None, "high": None,
                           "status": "no_reference", "title": None, "description": None})
            continue
        low, high = float(r.low), float(r.high)
        status = "low" if value < low else "high" if value > high else "normal"
        result.append({"index": name, "value": value, "low": low, "high": high,
                       "status": status, "title": r.title, "description": r.description})
    return result


def add_zones(indices: list[dict], zones: dict[str, dict[str, float]]) -> list[dict]:
    """Attach colour percentages and the dominant colour to each index result."""
    for item in indices:
        pct = zones.get(item["index"])
        item["zones"] = pct
        item["dominant_color"] = max(pct, key=pct.get) if pct else None
    return indices
