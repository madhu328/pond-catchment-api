# 🌊 JalDrishti — AI Village Pond Planning & Catchment Hydrology Platform

An interactive Web GIS Application & FastAPI Backend for **AI-Based Village Pond Planning & Catchment Hydrology Analysis**.

**Author:** Maloth Madhu (Student ID: 12341370)  
**Email:** [malothm@iitbhilai.ac.in](mailto:malothm@iitbhilai.ac.in)  
**Institution:** Department of Computer Science & Engineering, IIT Bhilai  
**Allocated System ID:** `stu29_sys2`  
**GitHub Repository:** [https://github.com/madhu328/pond-catchment-api](https://github.com/madhu328/pond-catchment-api)  

---

## 🚀 24/7 Deployed Live System URLs

The backend and frontend services are deployed and running **24/7** on the assigned campus server nodes:

| Service | Node / Port | Live Access URL | Description |
|---|---|---|---|
| **Frontend Web App** | `stu29_sys2:3000` (NAT: `3314`) | **[http://10.1.75.51:3314/](http://10.1.75.51:3314/)** | Pure Vanilla HTML/CSS/JS (Leaflet + Geoman + Chart.js) |
| **Backend REST API** | `stu29_sys2:4000` (NAT: `4314`) | **[http://10.1.75.51:4314/](http://10.1.75.51:4314/)** | FastAPI / Uvicorn Hydrology Analysis Engine |
| **Interactive API Docs** | `stu29_sys2:4000` (NAT: `4314`) | **[http://10.1.75.51:4314/docs](http://10.1.75.51:4314/docs)** | OpenAPI / Swagger Documentation UI |
| **Health Liveness Check**| `stu29_sys2:4000` (NAT: `4314`) | **[http://10.1.75.51:4314/api/v1/health](http://10.1.75.51:4314/api/v1/health)** | System Status Probe |
| **SSH Server Access** | `stu29_sys2:22` (NAT: `2314`) | `ssh -p 2314 student@10.1.75.51` | Remote Cluster Terminal |

---

## 🌟 Key Features

1. **Clean Separation of Concerns**:
   - Distinct, decoupled `frontend/` and `backend/` directories.
   - **Pure Vanilla JavaScript (Zero React)**: Ultra-fast loading ($<120$\,KB), zero node_modules dependencies, zero build/webpack steps.
   - **Zero WebSockets**: Relies entirely on clean, asynchronous, standard REST transactions.
   - **Embedded Reverse Proxy**: Frontend server (`serve_frontend.py`) proxies API calls directly to internal port 4000, eliminating CORS issues.

2. **Interactive Web Front-End (SPA)**:
   - Modern glassmorphism UI with dark theme and responsive panels.
   - **4 Basemap Options**: Satellite Imagery (Esri World Imagery), Topographic Terrain (OpenTopoMap), Dark Canvas (CartoDB), and OpenStreetMap.
   - **3 Selection Modes**:
     - ✏️ **Interactive Map Drawing**: Draw custom land boundary polygons directly on the map using Leaflet-Geoman.
     - 📁 **KML/KMZ Contour Upload**: Ingest standard 3D contour elevation maps.
     - 📌 **Regional Presets**: One-click demo datasets (Raipur Basin, Durg Watershed, Micro-Hilly Catchment).

3. **Map Overlays & Visualizations**:
   - 📍 **Suggested Pond Location Pin**: Animated glowing marker with elevation, coordinates, and recommended design depth.
   - 🔷 **Catchment Area Boundary**: Colored semi-transparent GeoJSON polygon overlaid on the map.
   - 💧 **Expected Water Volume Badge**: Overlaid directly at the pond site.

4. **Hydrological Calculation & Simulation**:
   - **Digital Elevation Model (DEM)**: Reconstructed via SciPy bivariate spline interpolation.
   - **D8 Flow Direction & Accumulation**: Evaluates steepest downward hydraulic gradient and routes overland drainage.
   - **USDA SCS-CN Runoff Model**: Estimates harvestable surface runoff from catchment area and precipitation depth.
   - **Community Impact**: Calculates estimated rural households served for 100 dry-season days.
   - **Pond Engineering Specifications**: Storage capacity ($m^3$ and Million Liters), surface area, top length/width, embankment slope.

5. **Analytics & Deliverables**:
   - Interactive Chart.js graphs: Catchment Elevation Profile & Monthly Water Harvest Hydrograph.
   - 📥 **Export GeoJSON**: Download GeoJSON feature collections of Pond Pins and Catchment Polygons.

---

## 📁 Project Directory Structure

```
pond_catchment/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration constants & formats
│   │   ├── kml_parser.py          # Vector contour parser (KML/KMZ)
│   │   ├── dem_builder.py         # SciPy spline DEM surface builder
│   │   ├── catchment.py           # D8 flow routing, accumulation & SCS-CN
│   │   └── main.py                # FastAPI endpoints & Pydantic models
│   ├── contours_1m.kml            # Sample 1-meter elevation contour dataset
│   ├── requirements.txt           # Python backend dependencies
│   ├── run_backend.py             # Uvicorn production server runner (Port 4000)
│   └── test_backend.py            # Automated test suite
├── frontend/
│   ├── index.html                 # Single-page web dashboard markup
│   ├── styles.css                 # Glassmorphic responsive styling
│   ├── app.js                     # Leaflet map, Geoman & Chart.js logic (Zero React)
│   └── serve_frontend.py          # Multi-threaded server & reverse-proxy (Port 3000)
├── report_final.tex               # Complete 10-page academic LaTeX technical report
├── run_backend_daemon.sh          # Self-healing watchdog daemon for backend
├── run_frontend_daemon.sh         # Self-healing watchdog daemon for frontend
├── start_all.sh                   # Detached process launcher & port verifier
└── README.md
```

---

## 🚀 Quick Start (Local Execution)

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend API server on port 4000
python3 run_backend.py 4000
```

### 2. Frontend Setup
```bash
cd frontend

# Run frontend server with reverse proxy targeting backend port 4000
python3 serve_frontend.py 3000 http://127.0.0.1:4000
```

Open your browser at **`http://localhost:3000/`** to interact with the application!

---

## 📡 Primary API Endpoints

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
  "rainfall_mm": 1185.4,
  "runoff_coefficient": 0.35
}
```

### `POST /analyzeContour` (or alias `POST /findCatchment`)
Accepts a KML/KMZ contour map and returns terrain flow & hydrological volume metrics.

**Parameters (`multipart/form-data`):**
- `contour_map`: `.kml` or `.kmz` file
- `rainfall_mm`: (optional, default `1000.0`)
- `runoff_coefficient`: (optional, default `0.35`)
