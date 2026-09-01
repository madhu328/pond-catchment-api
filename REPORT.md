# Assignment 1 - Phase 2: Pond Catchment Analysis Backend Report

**Author:** Madhu  
**Instructor:** Shivam Kushwaha  
**Submission Date:** September 2, 2026  
**Course Assignment:** Assignment 1 - Phase 2: Pond Catchment Analysis Backend  
**GitHub Repository:** [https://github.com/madhu328/pond-catchment-api](https://github.com/madhu328/pond-catchment-api)  

---

## 1. Project & API Route Overview

| Metric / Parameter | Value / Details |
| :--- | :--- |
| **GitHub Repository** | `https://github.com/madhu328/pond-catchment-api` |
| **Primary API Endpoint (Network / TA Access)** | `http://10.50.33.238:3313/analyzeContour` |
| **Local Machine Endpoint** | `http://localhost:3313/analyzeContour` |
| **Public WAN Endpoint** | `http://103.147.138.252:3313/analyzeContour` |
| **Alias Endpoint** | `http://10.50.33.238:3313/findCatchment` |
| **Required Form Field** | `contour_map` (File upload: `.kml` or `.kmz`) |
| **Fallback Form Field** | `file` |
| **HTTP Method** | `POST` |
| **Interactive Docs (Swagger UI)**| `http://10.50.33.238:3313/docs` (or `http://localhost:3313/docs`) |
| **Interactive Upload Interface**| `http://10.50.33.238:3313/` (or `http://localhost:3313/`) |

---

## 2. Catchment Estimation Approach & Methodology

The backend implements a **fully generalized hydrological & terrain analysis pipeline** that dynamically parses coordinate and elevation data from KML/KMZ files without relying on hardcoded coordinates or bounding boxes.

```
       +-------------------------------------------------------+
       |   Uploaded KML/KMZ File ('contour_map' form field)    |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |  1. Robust KML/KMZ Parser (XML / zipfile parsing)     |
       |     - Extracts 3D coordinates (Lon, Lat, Elevation)    |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |  2. DEM Builder (SciPy Grid Interpolation)            |
       |     - Projects points & generates regular elevation   |
       |       grid matrix (DEM)                               |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |  3. D8 Flow Direction & Flow Accumulation Algorithm   |
       |     - Calculates steepest slope direction & routes     |
       |       upstream cell drainage                          |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |  4. Pond Site Selection & Catchment Delineation       |
       |     - Selects natural convergence point (low elevation|
       |       + max flow accumulation)                        |
       |     - Backtracks contributing upstream area           |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |  5. Structured JSON Output Generation                 |
       |     - Lon/Lat, Elevation, Area (m² & Ha), Boundary    |
       +-------------------------------------------------------+
```

### Key Technical Steps:
1. **Dynamic KML/KMZ Parsing (`app/kml_parser.py`)**:
   - Parses XML placemarks, LineStrings, and Polygons.
   - Automatically unzips `.kmz` files to locate `doc.kml`.
   - Extracts all $(X, Y, Z)$ tuples where $X=\text{Longitude}$, $Y=\text{Latitude}$, $Z=\text{Elevation (meters)}$.

2. **Digital Elevation Model (DEM) Interpolation (`app/dem_builder.py`)**:
   - Converts geographic coordinates into an equidistant local meter-based grid.
   - Uses SciPy `griddata` (Cubic & Nearest-Neighbor interpolation) to build a continuous regular raster grid of elevation values.

3. **D8 Flow Routing & Accumulation (`app/catchment.py`)**:
   - Computes the direction of steepest descent from each cell to its 8 neighbors (D8 Flow Direction).
   - Resolves topological sorting to calculate **Flow Accumulation**—the exact number of upstream grid cells draining into each individual cell.

4. **Optimal Pond Placement (`app/catchment.py`)**:
   - Identifies cells combining high flow accumulation (high runoff collection potential) with low relative elevation.
   - Selects the optimal cell for village pond construction.

5. **Catchment Delineation & Area Calculation**:
   - Performs a recursive reverse traversal from the target pond cell to identify all contributing cells.
   - Calculates the exact catchment surface area:
     $$\text{Catchment Area } (m^2) = \text{Number of Contributing Cells} \times (\text{Grid Resolution})^2$$
   - Converts spatial cell boundaries back to geographic WGS84 $(Longitude, Latitude)$ polygon coordinates.

---

## 3. Demonstration on Provided Sample Map (`contours_1m.kml`)

### Execution Details
- **Input File:** `contours_1m.kml` (6.71 MB)
- **Processing Time:** ~2.1 seconds
- **Grid Resolution:** $10.0 \text{ meters/cell}$
- **Grid Dimensions:** $264 \times 324 \text{ cells}$

### Returned Results Summary
* **Recommended Pond Site Location:**
  * **Latitude:** `21.246056° N`
  * **Longitude:** `81.289336° E`
  * **Site Elevation:** `268.0 meters`
* **Catchment Hydrology:**
  * **Total Catchment Area:** `35,700.0 m²` (**3.57 Hectares**)
  * **Contributing Cells:** `357 cells`
  * **Minimum Catchment Elevation:** `268.0 m`
  * **Maximum Catchment Elevation:** `284.88 m`

---

## 4. API Specification & Documentation

### Endpoint Definition
* **URL:** `/analyzeContour` (or `/findCatchment`)
* **Method:** `POST`
* **Content-Type:** `multipart/form-data`

### Request Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `contour_map` | File (`.kml` / `.kmz`) | **Yes** | The contour map file containing 3D terrain geometries and elevation values. |

---

### Example cURL Command
```bash
curl -X POST "http://103.147.138.252:3313/analyzeContour" \
  -F "contour_map=@contours_1m.kml"
```

---

### Example Postman Setup
1. Set HTTP Method to `POST`.
2. Enter URL: `http://103.147.138.252:3313/analyzeContour`.
3. Under the **Body** tab, select **form-data**.
4. Set Key = `contour_map` (change type dropdown from *Text* to *File*).
5. Attach `contours_1m.kml`.
6. Click **Send**.

---

### Sample API Output (JSON)
```json
{
  "input_file": "contours_1m.kml",
  "processing_time_seconds": 2.1,
  "dem_resolution_meters": 10.0,
  "grid_size": {
    "rows": 264,
    "cols": 324
  },
  "recommended_pond_location": {
    "longitude": 81.28933599489764,
    "latitude": 21.24605558428102,
    "elevation_m": 268.0
  },
  "catchment": {
    "area_m2": 35700.0,
    "area_hectares": 3.57,
    "num_contributing_cells": 357,
    "elevation_min_m": 268.0,
    "elevation_max_m": 284.88,
    "boundary_polygon_lonlat": [
      [81.28846546444733, 21.24542323664919],
      [81.28807856202498, 21.245603907401144],
      [81.28788511081379, 21.24569424277712],
      [81.2877883852082, 21.245784578153092],
      [81.28759493399703, 21.245965248905044],
      [81.28749820839144, 21.246416925784924],
      [81.28769165960261, 21.246958938040777],
      [81.28807856202498, 21.247410614920657],
      [81.28827201323615, 21.247591285672605],
      [81.2887556412641, 21.247591285672605],
      [81.28894909247528, 21.247410614920657],
      [81.28933599489764, 21.247049273416753],
      [81.2896261717144, 21.24668793191285],
      [81.28933599489764, 21.24605558428102],
      [81.28856219005291, 21.24542323664919],
      [81.28846546444733, 21.24542323664919]
    ]
  },
  "note": "Runoff volume and rainfall-based storage estimates will be integrated in the next phase using a rainfall API, using this catchment area as the input."
}
```

---

## 5. Code Extensibility & Future Phase Readiness

1. **Modular Architecture:**
   * `app/kml_parser.py`: Standalone parser supporting any standard KML/KMZ containing point, linestring, or polygon contour elements.
   * `app/dem_builder.py`: Independent DEM generator scalable to custom grid resolutions.
   * `app/catchment.py`: Pure mathematical D8 hydrology engine.
   * `app/main.py`: Clean RESTful API wrapper using FastAPI.

2. **Phase 3 Integration Readiness:**
   * The calculated catchment area (`35,700.0 m²` / `3.57 ha`) directly serves as the input parameter for precipitation runoff equations ($Q = C \cdot I \cdot A$).
   * Future rainfall APIs (Open-Meteo / IMD) can easily query historical or real-time precipitation data ($I$) using the `recommended_pond_location` coordinates ($21.246056^\circ \text{N}, 81.289336^\circ \text{E}$).
