# 🌊 JalDrishti — AI Village Pond & Catchment Hydrology Platform

An interactive Web Application & FastAPI Backend for **AI-Based Village Pond Planning & Catchment Hydrology Analysis**.

It allows users to select land areas on an interactive map (or upload KML/KMZ contour maps), computes terrain D8 flow direction and accumulation, identifies optimal low-lying pond placement, delineates the catchment basin boundary, and calculates harvestable water volume ($V = C \times P \times A$).

---

## 🌟 Key Features

1. **Interactive Web Front-End (SPA)**:
   - Built with modern glassmorphism design, dark theme, and Leaflet.js interactive maps.
   - **4 Basemap Options**: Satellite Imagery (Esri World Imagery), Topographic Terrain (OpenTopoMap), Dark Canvas (CartoDB), and OpenStreetMap.
   - **3 Selection Modes**:
     - ✏️ **Interactive Map Drawing**: Draw custom land boundary polygons directly on the map.
     - 📁 **KML/KMZ Contour Upload**: Drag & drop contour elevation maps.
     - 📌 **Regional Presets**: One-click demo datasets (Raipur Basin, Durg Watershed, Hilly Catchment).

2. **Map Overlays & Visualizations**:
   - 📍 **Suggested Pond Location Pin**: Animated glowing marker with elevation, coordinates, and recommended design depth.
   - 🔷 **Catchment Area Boundary**: Colored semi-transparent GeoJSON polygon overlaid on the map.
   - 💧 **Expected Water Volume Badge**: Overlaid directly at the pond site.

3. **Hydrological Calculation & Simulation**:
   - **Rational Method Runoff**: $V = C \times P \times A$ ($m^3$, Liters, Million Liters).
   - **Real-Time Sliders**: Adjust Annual Rainfall ($P$ in mm), Soil/Land Runoff Coefficient ($C$), and Pond Target Depth ($m$) with instant client-side recalculation.
   - **Community Impact**: Calculates estimated rural households served for 100 dry-season days.
   - **Pond Engineering Specifications**: Storage capacity, surface area, top length/width, embankment slope.

4. **Analytics & Deliverables**:
   - Interactive Chart.js graphs: Catchment Elevation Profile & Monthly Water Harvest Hydrograph.
   - 📥 **Export GeoJSON**: Download GeoJSON feature collections of Pond Pins and Catchment Polygons.

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone repository
git clone <repository-url>
cd pond_backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Application
```bash
# Option A: Helper runner script (default port 3313)
python run_server.py 3313

# Option B: Direct uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 3313
```

Open your browser at **`http://127.0.0.1:3313/`** to view the interactive map web app!

---

## 📡 API Endpoints

### `POST /analyzeContour` or `POST /findCatchment`
Accepts a KML/KMZ contour map and returns terrain flow & hydrological volume metrics.

**Parameters (`multipart/form-data`):**
- `contour_map`: `.kml` or `.kmz` file
- `rainfall_mm`: (optional, default `1000.0`) Annual monsoon rainfall in mm.
- `runoff_coefficient`: (optional, default `0.35`) Soil runoff coefficient $C$.

### `POST /analyzeSelectedArea`
Accepts a user-selected polygon drawn on the map.

**Request Body (`application/json`):**
```json
{
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
```

**Response Example (200 OK):**
```json
{
  "input_file": "contours_1m.kml",
  "processing_time_seconds": 1.25,
  "dem_resolution_meters": 10.0,
  "recommended_pond_location": {
    "longitude": 81.2893,
    "latitude": 21.2461,
    "elevation_m": 268.0
  },
  "catchment": {
    "area_m2": 35700.0,
    "area_hectares": 3.57,
    "num_contributing_cells": 357,
    "boundary_polygon_lonlat": [[81.288, 21.245], ["..."]]
  },
  "expected_water_volume": {
    "rainfall_mm": 1000.0,
    "runoff_coefficient": 0.35,
    "expected_volume_m3": 12495.0,
    "expected_volume_liters": 12495000.0,
    "expected_volume_million_liters": 12.495,
    "estimated_households_served": 166
  },
  "recommended_pond_dimensions": {
    "target_storage_capacity_m3": 10620.75,
    "recommended_depth_m": 3.0,
    "surface_area_m2": 3540.25,
    "estimated_length_m": 66.5,
    "estimated_width_m": 53.2,
    "embankment_slope": "1:1.5"
  }
}
```

---

## 🧮 Hydrological Method & Algorithm

1. **DEM Grid Interpolation**: Scipy linear grid interpolation converts scattered contour samples to a 10m regular Digital Elevation Model grid.
2. **D8 Flow Direction**: Determines steepest downhill neighbor for all cells.
3. **Flow Accumulation**: Walks cells from highest to lowest elevation, accumulating total upstream drainage cells.
4. **Pond Site Selection**: Identifies maximum flow convergence sink while excluding boundary edge artifacts.
5. **Catchment Delineation**: Reverse graph traversal from chosen pond cell collects all contributing upstream cells.
6. **Water Volume Calculation**: Rational Method formula:
   $$V = C \times P \times A$$
   where $A$ = Catchment Area ($m^2$), $P$ = Annual Monsoon Rainfall ($m$), $C$ = Runoff Coefficient.

---

## 📁 Project Structure

```
pond_backend/
├── app/
│   ├── main.py              # FastAPI app & static SPA routes
│   ├── kml_parser.py         # KML/KMZ contour parser
│   ├── dem_builder.py        # DEM elevation grid generator
│   └── catchment.py          # D8 flow algorithms & water volume logic
├── static/
│   ├── index.html           # Single Page Application HTML layout
│   ├── styles.css           # Glassmorphism design system
│   └── app.js               # Leaflet map, drawing tools & Chart.js logic
├── test_backend_direct.py   # Unit test runner
├── sample_output.json         # Example API output JSON
├── requirements.txt
├── run_server.py            # Server launcher script
└── README.md
```
