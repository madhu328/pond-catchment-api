"""
main.py
-------
FastAPI application exposing the /analyzeContour endpoint.

Run locally with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs (Swagger UI),
or POST a .kml/.kmz file to http://127.0.0.1:8000/analyzeContour
"""

import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_EXTENSIONS
from app.kml_parser import parse_contour_file
from app.dem_builder import build_dem
from app.catchment import (
    compute_flow_direction,
    compute_flow_accumulation,
    select_pond_site,
    delineate_catchment,
    catchment_boundary_lonlat,
)

app = FastAPI(
    title="Village Pond Catchment Analysis API",
    description="Accepts a contour map (KML/KMZ) and returns a recommended "
                 "pond location with its estimated catchment area.",
    version="0.1.0",
)

# Allow the frontend (running on a different port/origin) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Village Pond Catchment API is running"}


@app.post("/analyzeContour")
async def analyze_contour(
    contour_map: UploadFile = File(None),
    file: UploadFile = File(None),
):
    """
    Accepts a contour map file (.kml or .kmz) under form field 'contour_map'
    (or 'file'), analyzes the terrain, and returns:
      - a recommended pond location (lon/lat)
      - the estimated catchment area draining into that location
      - a boundary polygon of the catchment (for map overlay)
      - basic elevation statistics of the analyzed region

    Nothing about the sample map is hard-coded - every value below is
    derived from whatever contour file is uploaded.
    """
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
        "note": (
            "Runoff volume and rainfall-based storage estimates will be "
            "integrated in the next phase using a rainfall API, using this "
            "catchment area as the input."
        ),
    }


@app.post("/findCatchment")
async def find_catchment(
    contour_map: UploadFile = File(None),
    file: UploadFile = File(None),
):
    """Alias for /analyzeContour endpoint."""
    return await analyze_contour(contour_map=contour_map, file=file)