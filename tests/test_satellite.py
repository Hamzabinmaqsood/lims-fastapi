from shapely.geometry import Polygon

from app.integrations import sentinel
from tests.test_farms import SQUARE, login_as

FAKE_PNG = b"\x89PNG\r\n\x1a\nfake"


async def make_farm(client) -> tuple[dict, int]:
    h = await login_as(client, "03001111111")
    farm_id = (await client.post("/api/farms/", headers=h, json={"name": "Test", "boundary": SQUARE})).json()["id"]
    return h, farm_id


async def test_returns_png(client, monkeypatch):
    async def fake_fetch(poly, index):
        assert index == "NDVI"
        return FAKE_PNG

    monkeypatch.setattr(sentinel, "fetch_index_png", fake_fetch)
    h, farm_id = await make_farm(client)
    r = await client.get(f"/api/farms/{farm_id}/satellite/NDVI/", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content == FAKE_PNG


async def test_other_users_farm_404(client, monkeypatch):
    monkeypatch.setattr(sentinel, "fetch_index_png", lambda *a: FAKE_PNG)
    _, farm_id = await make_farm(client)
    other = await login_as(client, "03002222222")
    assert (await client.get(f"/api/farms/{farm_id}/satellite/NDVI/", headers=other)).status_code == 404


async def test_unknown_index_422(client):
    h, farm_id = await make_farm(client)
    assert (await client.get(f"/api/farms/{farm_id}/satellite/XYZ/", headers=h)).status_code == 422


def test_request_uses_lng_lat_and_keeps_shape():
    poly = Polygon([(74.35, 31.52), (74.351, 31.52), (74.351, 31.521), (74.35, 31.521)])
    req = sentinel.build_request(poly, "NDMI")
    first_point = req["input"]["bounds"]["geometry"]["coordinates"][0][0]
    assert first_point == (74.35, 31.52)  # GeoJSON is (lng, lat)
    w, h = req["output"]["width"], req["output"]["height"]
    assert w < h  # ~0.001° wide is fewer metres than ~0.001° tall at lat 31.5
    assert "s.B11" in req["evalscript"]  # NDMI uses the SWIR band

def stats_item(day: str, missing: int, ndvi: float) -> dict:
    band = lambda mean: {"bands": {"B0": {"stats": {"mean": mean, "sampleCount": 100, "noDataCount": missing}}}}
    return {
        "interval": {"from": f"{day}T00:00:00Z", "to": f"{day}T23:59:59Z"},
        "outputs": {name.lower(): band(ndvi) for name in sentinel.FORMULAS},
    }


def test_latest_clear_stats_skips_cloudy_days():
    body = {"data": [
        stats_item("2026-11-01", missing=0, ndvi=0.41),   # clear, older
        stats_item("2026-11-06", missing=90, ndvi=0.05),  # newest but 90% cloud → skipped
    ]}
    result = sentinel.latest_clear_stats(body)
    assert result["date"] == "2026-11-01"
    assert result["indices"]["NDVI"] == 0.41
    assert result["clear_pct"] == 100


def test_all_cloudy_returns_none():
    assert sentinel.latest_clear_stats({"data": [stats_item("2026-11-06", 80, 0.1)]}) is None


def test_stats_evalscript_has_all_indices():
    script = sentinel.stats_evalscript()
    for name in sentinel.FORMULAS:
        assert f'id: "{name.lower()}"' in script
    assert "SCL" in script


async def test_stats_endpoint(client, monkeypatch):
    async def fake_stats(poly, days=30):
        return {"date": "2026-11-06", "clear_pct": 95, "indices": {"NDVI": 0.52}}

    monkeypatch.setattr(sentinel, "fetch_index_stats", fake_stats)
    h, farm_id = await make_farm(client)
    r = await client.get(f"/api/farms/{farm_id}/satellite/stats/", headers=h)
    assert r.status_code == 200  # 422 here would mean the route order is wrong
    assert r.json()["indices"]["NDVI"] == 0.52


async def test_stats_no_clear_image_404(client, monkeypatch):
    async def fake_stats(poly, days=30):
        return None

    monkeypatch.setattr(sentinel, "fetch_index_stats", fake_stats)
    h, farm_id = await make_farm(client)
    assert (await client.get(f"/api/farms/{farm_id}/satellite/stats/", headers=h)).status_code == 404
