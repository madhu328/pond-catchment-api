"""
main.py
-------
FastAPI application exposing /analyzeContour, /findCatchment, and /analyzeSelectedArea endpoints,
and serving the modern interactive map front-end application.
"""

import os
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import ALLOWED_EXTENSIONS
from app.kml_parser import parse_contour_file
from app.dem_builder import build_dem, build_dem_from_polygon
from app.catchment import (
    compute_flow_direction,
    compute_flow_accumulation,
    select_pond_site,
    delineate_catchment,
    catchment_boundary_lonlat,
    calculate_expected_water_volume,
    calculate_pond_dimensions,
)

app = FastAPI(
    title="Village Pond Catchment & Hydrological Analysis API",
    description="Accepts contour maps (KML/KMZ) or interactive map land selections, "
                "analyzes D8 terrain drainage, determines optimal pond placement, "
                "delineates catchment boundary, and calculates expected water volume.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists and mount static files
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MapAreaRequest(BaseModel):
    polygon_lonlat: List[List[float]]
    rainfall_mm: Optional[float] = 1000.0
    runoff_coefficient: Optional[float] = 0.35


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Village Pond Backend Running. Static frontend index.html not found.</h2>")


@app.post("/analyzeSelectedArea")
async def analyze_selected_area(data: MapAreaRequest):
    """
    Analyzes a user-selected land area polygon drawn on the interactive map.
    """
    if not data.polygon_lonlat or len(data.polygon_lonlat) < 3:
        raise HTTPException(
            status_code=400,
            detail="At least 3 polygon [lon, lat] coordinates are required."
        )

    start = time.time()
    rainfall_mm = data.rainfall_mm if data.rainfall_mm is not None else 1000.0
    runoff_coeff = data.runoff_coefficient if data.runoff_coefficient is not None else 0.35

    # 1. Build DEM grid from selected land area polygon
    dem = build_dem_from_polygon(data.polygon_lonlat, cell_size=10.0)

    # 2. Terrain Analysis (D8 flow direction & accumulation)
    down_row, down_col = compute_flow_direction(dem)
    acc = compute_flow_accumulation(dem, down_row, down_col)

    # 3. Recommended pond location
    pond_row, pond_col = select_pond_site(dem, acc, down_row, down_col)
    pond_lon, pond_lat = dem.local_to_lonlat(
        dem.x_coords[pond_col], dem.y_coords[pond_row]
    )
    pond_elevation = float(dem.elevation[pond_row, pond_col])

    # 4. Catchment delineation
    catchment_cells = delineate_catchment(down_row, down_col, pond_row, pond_col)
    cell_area_m2 = dem.cell_size ** 2
    catchment_area_m2 = len(catchment_cells) * cell_area_m2
    boundary = catchment_boundary_lonlat(dem, catchment_cells)

    catchment_elevations = [float(dem.elevation[r, c]) for r, c in catchment_cells]

    # 5. Hydrological Water Volume & Pond Dimensions Calculation
    water_vol = calculate_expected_water_volume(catchment_area_m2, rainfall_mm, runoff_coeff)
    pond_dims = calculate_pond_dimensions(water_vol["expected_volume_m3"])

    elapsed = round(time.time() - start, 2)

    return {
        "input_type": "interactive_map_selection",
        "processing_time_seconds": elapsed,
        "dem_resolution_meters": round(dem.cell_size, 2),
        "grid_size": {"rows": dem.elevation.shape[0], "cols": dem.elevation.shape[1]},
        "recommended_pond_location": {
            "longitude": pond_lon,
            "latitude": pond_lat,
            "elevation_m": pond_elevation,
        },
        "catchment": {
            "area_m2": round(catchment_area_m2, 2),
            "area_hectares": round(catchment_area_m2 / 10_000, 3),
            "num_contributing_cells": len(catchment_cells),
            "elevation_min_m": round(min(catchment_elevations), 2),
            "elevation_max_m": round(max(catchment_elevations), 2),
            "boundary_polygon_lonlat": boundary,
        },
        "expected_water_volume": water_vol,
        "recommended_pond_dimensions": pond_dims,
    }


@app.post("/analyzeContour")
@app.post("/findCatchment")
async def handle_contour_request(
    request: Request,
    contour_map: UploadFile = File(None),
    file: UploadFile = File(None),
    rainfall_mm: float = Form(1000.0),
    runoff_coefficient: float = Form(0.35),
):
    upload = contour_map or file
    if upload is None:
        raise HTTPException(
            status_code=400,
            detail="Missing file. Please upload a .kml or .kmz file under form parameter 'contour_map'."
        )

    if not upload.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Please upload a .kml or .kmz file.")

    file_bytes = await upload.read()
    start = time.time()

    # 1. Parse contour lines out of the uploaded file
    try:
        contours = parse_contour_file(upload.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse contour file: {e}")

    # 2. Build a regular elevation grid (DEM) from the contour lines
    dem = build_dem(contours)

    # 3. Terrain analysis: flow direction -> flow accumulation
    down_row, down_col = compute_flow_direction(dem)
    acc = compute_flow_accumulation(dem, down_row, down_col)

    # 4. Pick the recommended pond site (natural drainage convergence point)
    pond_row, pond_col = select_pond_site(dem, acc, down_row, down_col)
    pond_lon, pond_lat = dem.local_to_lonlat(
        dem.x_coords[pond_col], dem.y_coords[pond_row]
    )
    pond_elevation = float(dem.elevation[pond_row, pond_col])

    # 5. Delineate the catchment area feeding that site
    catchment_cells = delineate_catchment(down_row, down_col, pond_row, pond_col)
    cell_area_m2 = dem.cell_size ** 2
    catchment_area_m2 = len(catchment_cells) * cell_area_m2
    boundary = catchment_boundary_lonlat(dem, catchment_cells)

    catchment_elevations = [
        float(dem.elevation[r, c]) for r, c in catchment_cells
    ]

    # 6. Expected Water Volume & Pond Engineering Dimensions
    water_vol = calculate_expected_water_volume(catchment_area_m2, rainfall_mm, runoff_coefficient)
    pond_dims = calculate_pond_dimensions(water_vol["expected_volume_m3"])

    elapsed = round(time.time() - start, 2)

    return {
        "input_file": upload.filename,
        "processing_time_seconds": elapsed,
        "dem_resolution_meters": round(dem.cell_size, 2),
        "grid_size": {"rows": dem.elevation.shape[0], "cols": dem.elevation.shape[1]},
        "recommended_pond_location": {
            "longitude": pond_lon,
            "latitude": pond_lat,
            "elevation_m": pond_elevation,
        },
        "catchment": {
            "area_m2": round(catchment_area_m2, 2),
            "area_hectares": round(catchment_area_m2 / 10_000, 3),
            "num_contributing_cells": len(catchment_cells),
            "elevation_min_m": round(min(catchment_elevations), 2),
            "elevation_max_m": round(max(catchment_elevations), 2),
            "boundary_polygon_lonlat": boundary,
        },
        "expected_water_volume": water_vol,
        "recommended_pond_dimensions": pond_dims,
        "note": "Water volume calculated using Rational Method V = C * P * A.",
    }