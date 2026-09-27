"""
test_app_unit.py
----------------
Unit test script to verify FastAPI app routes, static file serving,
water volume calculations, and terrain analysis endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_routes():
    print("1. Testing GET / (Frontend SPA index.html)...")
    res_index = client.get("/")
    assert res_index.status_code == 200, f"Expected 200 OK, got {res_index.status_code}"
    assert "JalDrishti" in res_index.text, "Index HTML missing JalDrishti title"
    print("   [SUCCESS] GET / returned index.html SPA successfully.")

    print("2. Testing POST /analyzeContour with contours_1m.kml...")
    kml_path = "contours_1m.kml"
    if os.path.exists(kml_path):
        with open(kml_path, "rb") as f:
            res_contour = client.post(
                "/analyzeContour",
                files={"contour_map": ("contours_1m.kml", f, "application/vnd.google-earth.kml+xml")},
                data={"rainfall_mm": 1200.0, "runoff_coefficient": 0.35}
            )
        assert res_contour.status_code == 200, f"Expected 200, got {res_contour.status_code}: {res_contour.text}"
        data = res_contour.json()

        assert "recommended_pond_location" in data, "Missing recommended_pond_location"
        assert "catchment" in data, "Missing catchment"
        assert "expected_water_volume" in data, "Missing expected_water_volume"
        assert "recommended_pond_dimensions" in data, "Missing recommended_pond_dimensions"

        pond = data["recommended_pond_location"]
        catchment = data["catchment"]
        vol = data["expected_water_volume"]

        print(f"   [SUCCESS] Pond Site: ({pond['latitude']:.4f}, {pond['longitude']:.4f}) Elev: {pond['elevation_m']}m")
        print(f"   [SUCCESS] Catchment Area: {catchment['area_hectares']} ha ({catchment['area_m2']} m²)")
        print(f"   [SUCCESS] Expected Water Volume: {vol['expected_volume_m3']} m³ ({vol['expected_volume_million_liters']} Million Liters)")
        print(f"   [SUCCESS] Households Served: {vol['estimated_households_served']} households")

    print("3. Testing POST /analyzeSelectedArea (Interactive Map Polygon)...")
    poly_payload = {
        "polygon_lonlat": [
            [81.2850, 21.2430],
            [81.2930, 21.2430],
            [81.2930, 21.2490],
            [81.2850, 21.2490],
            [81.2850, 21.2430]
        ],
        "rainfall_mm": 1000.0,
        "runoff_coefficient": 0.35
    }
    res_area = client.post("/analyzeSelectedArea", json=poly_payload)
    assert res_area.status_code == 200, f"Expected 200, got {res_area.status_code}: {res_area.text}"
    area_data = res_area.json()

    assert area_data["input_type"] == "interactive_map_selection"
    assert "recommended_pond_location" in area_data
    assert "expected_water_volume" in area_data

    print(f"   [SUCCESS] Interactive Map Area Analysis Passed.")
    print("ALL UNIT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_routes()
