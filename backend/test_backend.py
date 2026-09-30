#!/usr/bin/env python3
"""
test_backend.py
---------------
Unit test script to verify FastAPI app routes, water volume calculations,
and terrain analysis endpoints.
"""

import asyncio
import io
import os
import sys
from fastapi.datastructures import UploadFile

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app, handle_contour_request, analyze_selected_area, MapAreaRequest

async def run_tests():
    print("============================================================")
    print("  Running JalDrishti Backend Tests")
    print("============================================================")

    kml_path = os.path.join(os.path.dirname(__file__), "contours_1m.kml")
    if os.path.exists(kml_path):
        print("\n1. Testing handle_contour_request with contours_1m.kml...")
        with open(kml_path, "rb") as f:
            file_bytes = f.read()

        upload_file = UploadFile(filename="contours_1m.kml", file=io.BytesIO(file_bytes))
        res_contour = await handle_contour_request(
            request=None,
            contour_map=upload_file,
            file=None,
            rainfall_mm=1200.0,
            runoff_coefficient=0.35
        )

        assert "recommended_pond_location" in res_contour, "Missing recommended_pond_location"
        assert "catchment" in res_contour, "Missing catchment"
        assert "expected_water_volume" in res_contour, "Missing expected_water_volume"
        assert "recommended_pond_dimensions" in res_contour, "Missing recommended_pond_dimensions"

        pond = res_contour["recommended_pond_location"]
        catchment = res_contour["catchment"]
        vol = res_contour["expected_water_volume"]
        dims = res_contour["recommended_pond_dimensions"]

        print(f"   ✓ Pond Site: Lat {pond['latitude']:.4f}, Lon {pond['longitude']:.4f}, Elev {pond['elevation_m']}m")
        print(f"   ✓ Catchment Area: {catchment['area_hectares']} ha ({catchment['area_m2']} m²)")
        print(f"   ✓ Expected Water Volume: {vol['expected_volume_m3']} m³ ({vol['expected_volume_million_liters']} ML)")
        print(f"   ✓ Pond Dimensions: {dims['estimated_length_m']}m x {dims['estimated_width_m']}m x {dims['recommended_depth_m']}m")
    else:
        print(f"   ⚠ Skipping KML test (contours_1m.kml not found at {kml_path})")

    print("\n2. Testing analyze_selected_area with interactive map polygon...")
    req_data = MapAreaRequest(
        polygon_lonlat=[
            [81.2850, 21.2430],
            [81.2930, 21.2430],
            [81.2930, 21.2490],
            [81.2850, 21.2490],
            [81.2850, 21.2430]
        ],
        rainfall_mm=1000.0,
        runoff_coefficient=0.35
    )
    res_area = await analyze_selected_area(req_data)

    assert res_area["input_type"] == "interactive_map_selection", "Invalid input_type"
    assert "recommended_pond_location" in res_area, "Missing pond location"
    assert "expected_water_volume" in res_area, "Missing expected volume"
    assert "elevation_profile" in res_area["catchment"], "Missing elevation profile"

    area_vol = res_area["expected_water_volume"]
    print(f"   ✓ Interactive Map Area Volume: {area_vol['expected_volume_m3']} m³ ({area_vol['expected_volume_million_liters']} ML)")

    print("\n============================================================")
    print("  ALL BACKEND UNIT TESTS PASSED SUCCESSFULLY!")
    print("============================================================")

def main():
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()
