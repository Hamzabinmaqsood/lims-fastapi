import io

from openpyxl import Workbook

from tests.test_growth_stages import setup

HEADER = "Interval Days,Growth Stage,NDVI Low,NDVI High,NDVI Title,RECL Low,RECL High\n"
GOOD_CSV = HEADER + "0-20,Germination,0.10,0.30,Emerging,0.05,0.20\n21-45,Tillering,0.35,0.72,Good,,\n"


def csv_file(text: str, name: str = "stages.csv"):
    return {"file": (name, text.encode(), "text/csv")}


async def test_csv_import_creates_stages(client):
    farmer, admin = await setup(client)
    r = await client.post("/api/growth-stages/import/", headers=admin,
                          data={"crop_id": "1"}, files=csv_file(GOOD_CSV))
    assert r.status_code == 200
    assert r.json()["imported"] == 2

    stages = (await client.get("/api/growth-stages/", headers=farmer, params={"crop_id": 1})).json()
    assert [s["name"] for s in stages] == ["Germination", "Tillering"]
    assert [x["index_name"] for x in stages[0]["ranges"]] == ["NDVI", "RECI"]  # RECL → RECI


async def test_import_replaces_old_stages(client):
    _, admin = await setup(client)
    await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"}, files=csv_file(GOOD_CSV))
    one_row = HEADER + "0-30,Early,0.1,0.4,,,\n"
    await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"}, files=csv_file(one_row))
    stages = (await client.get("/api/growth-stages/", headers=admin, params={"crop_id": 1})).json()
    assert [s["name"] for s in stages] == ["Early"]


async def test_bad_row_imports_nothing(client):
    _, admin = await setup(client)
    bad = HEADER + "0-20,Germination,0.10,0.30,,,\n21-45,Tillering,0.90,0.20,,,\n"  # row 3: low > high
    r = await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"}, files=csv_file(bad))
    assert r.status_code == 400
    assert r.json()["detail"]["errors"][0]["row"] == 3

    stages = (await client.get("/api/growth-stages/", headers=admin, params={"crop_id": 1})).json()
    assert stages == []  # all-or-nothing


async def test_xlsx_import(client):
    _, admin = await setup(client)
    wb = Workbook()
    wb.active.append(["Interval Days", "Growth Stage", "NDVI Low", "NDVI High"])
    wb.active.append(["0-20", "Germination", 0.1, 0.3])
    buf = io.BytesIO()
    wb.save(buf)
    r = await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"},
                          files={"file": ("stages.xlsx", buf.getvalue(),
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200


async def test_wrong_file_type_400(client):
    _, admin = await setup(client)
    r = await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"},
                          files=csv_file("hello", name="stages.txt"))
    assert r.status_code == 400


async def test_farmer_cannot_import_403(client):
    farmer, _ = await setup(client)
    r = await client.post("/api/growth-stages/import/", headers=farmer,
                          data={"crop_id": "1"}, files=csv_file(GOOD_CSV))
    assert r.status_code == 403


async def test_underscore_headers(client):
    _, admin = await setup(client)
    text = "Interval Days,Growth Stage,SAVI_LOW,SAVI_HIGH\n0-20,Germination,0.08,0.15\n"
    await client.post("/api/growth-stages/import/", headers=admin, data={"crop_id": "1"}, files=csv_file(text))
    stages = (await client.get("/api/growth-stages/", headers=admin, params={"crop_id": 1})).json()
    assert stages[0]["ranges"][0]["index_name"] == "SAVI"
