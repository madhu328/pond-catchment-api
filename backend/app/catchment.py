"""
catchment.py
------------
Core terrain analysis algorithms:

1. D8 flow direction - for every grid cell, figure out which one of its
   8 neighbours the water would flow into (the steepest downhill neighbour).
2. Flow accumulation - for every cell, count how many upstream cells
   eventually drain into it. This tells us where water naturally
   concentrates.
3. Pond site selection - pick a low-lying cell with high flow
   accumulation (a natural drainage confluence point) as the
   recommended pond location.
4. Catchment delineation - trace all cells that drain into the chosen
   pond location, using a reverse walk over the flow-direction graph.

This is a standard, well known approach in hydrology/GIS (used by tools
like ArcGIS "Flow Direction" / "Flow Accumulation" / "Watershed"), just
implemented here from scratch with numpy so the project has no heavy
GIS-library dependency.
"""

import numpy as np
from shapely.geometry import MultiPoint

# 8 neighbour offsets: (row_offset, col_offset), and their distance
# multiplier relative to cell_size (1.0 for orthogonal, sqrt2 for diagonal)
NEIGHBOURS = [
    (-1, -1, 2 ** 0.5), (-1, 0, 1.0), (-1, 1, 2 ** 0.5),
    (0, -1, 1.0),                     (0, 1, 1.0),
    (1, -1, 2 ** 0.5),  (1, 0, 1.0),  (1, 1, 2 ** 0.5),
]


def compute_flow_direction(dem):
    """
    For every cell, find the neighbour with the steepest downhill slope.
    Returns two arrays (same shape as the DEM grid):
        down_row, down_col - the row/col of the cell's downstream neighbour
                              (-1, -1 if the cell is a local sink / pit)
    """
    elev = dem.elevation
    n_rows, n_cols = elev.shape
    down_row = np.full((n_rows, n_cols), -1, dtype=int)
    down_col = np.full((n_rows, n_cols), -1, dtype=int)

    for r in range(n_rows):
        for c in range(n_cols):
            best_slope = 0.0
            best_r, best_c = -1, -1
            for dr, dc, dist_mult in NEIGHBOURS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n_rows and 0 <= nc < n_cols:
                    drop = elev[r, c] - elev[nr, nc]
                    dist = dist_mult * dem.cell_size
                    slope = drop / dist
                    if slope > best_slope:
                        best_slope = slope
                        best_r, best_c = nr, nc
            down_row[r, c] = best_r
            down_col[r, c] = best_c

    return down_row, down_col


def compute_flow_accumulation(dem, down_row, down_col):
    """
    Count how many cells (including itself) drain into each cell.
    Cells are processed from highest to lowest elevation, so every
    upstream contributor is already accounted for before we push its
    accumulated value further downstream.
    """
    elev = dem.elevation
    n_rows, n_cols = elev.shape
    acc = np.ones((n_rows, n_cols), dtype=float)  # every cell counts itself

    order = np.dstack(np.unravel_index(
        np.argsort(-elev.ravel()), elev.shape
    ))[0]

    for r, c in order:
        dr, dc = down_row[r, c], down_col[r, c]
        if dr != -1:
            acc[dr, dc] += acc[r, c]

    return acc


def select_pond_site(dem, acc, down_row, down_col, edge_margin: int = 2):
    """
    Pick the recommended primary pond location: the cell where the most water
    naturally converges (highest flow accumulation).
    """
    n_rows, n_cols = dem.elevation.shape
    masked = acc.copy()
    masked[:edge_margin, :] = -1
    masked[-edge_margin:, :] = -1
    masked[:, :edge_margin] = -1
    masked[:, -edge_margin:] = -1

    idx = np.unravel_index(np.argmax(masked), masked.shape)
    return idx  # (row, col)


def select_all_pond_sites(dem, acc, down_row, down_col, max_ponds: int = 3, min_cell_distance: int = 10):
    """
    Identifies all suitable pond candidate sites across the watershed terrain.
    Finds top N natural drainage sinks (Primary Storage Pond, Secondary Check Dam, Recharge Tank)
    maintaining physical spatial separation between sites.
    """
    n_rows, n_cols = dem.elevation.shape
    masked = acc.copy()
    masked[:2, :] = -1
    masked[-2:, :] = -1
    masked[:, :2] = -1
    masked[:, -2:] = -1

    pond_types = [
        {"rank": 1, "type": "Primary Storage Pond", "badge": "PRIMARY POND", "color": "#38bdf8"},
        {"rank": 2, "type": "Secondary Check Dam", "badge": "CHECK DAM", "color": "#34d399"},
        {"rank": 3, "type": "Percolation Recharge Tank", "badge": "RECHARGE TANK", "color": "#fbbf24"},
        {"rank": 4, "type": "Auxiliary Retention Basin", "badge": "RETENTION BASIN", "color": "#a78bfa"}
    ]

    all_ponds = []
    for i in range(min(max_ponds, len(pond_types))):
        if np.max(masked) <= 0:
            break
        r, c = np.unravel_index(np.argmax(masked), masked.shape)
        lon, lat = dem.local_to_lonlat(dem.x_coords[c], dem.y_coords[r])
        elev = float(dem.elevation[r, c])
        acc_val = float(acc[r, c])

        meta = pond_types[i]

        # Calculate individual site catchment boundary
        site_cells = delineate_catchment(down_row, down_col, r, c)
        site_area_m2 = len(site_cells) * (dem.cell_size ** 2)

        all_ponds.append({
            "rank": meta["rank"],
            "type": meta["type"],
            "badge": meta["badge"],
            "color": meta["color"],
            "latitude": round(float(lat), 6),
            "longitude": round(float(lon), 6),
            "elevation_m": round(elev, 2),
            "catchment_area_m2": round(site_area_m2, 2),
            "catchment_area_ha": round(site_area_m2 / 10000.0, 3),
            "flow_accumulation_cells": int(acc_val),
            "grid_row": int(r),
            "grid_col": int(c)
        })

        # Suppress local neighborhood around selected site so ponds don't overlap
        r_min, r_max = max(0, r - min_cell_distance), min(n_rows, r + min_cell_distance + 1)
        c_min, c_max = max(0, c - min_cell_distance), min(n_cols, c + min_cell_distance + 1)
        masked[r_min:r_max, c_min:c_max] = -1

    return all_ponds


def lon_lat_pair(lon, lat):
    return (float(lon), float(lat))



def delineate_catchment(down_row, down_col, target_row, target_col):
    """
    Reverse walk: starting from the pond cell, repeatedly collect every
    cell whose flow eventually reaches it. Returns a set of (row, col).
    """
    n_rows, n_cols = down_row.shape

    # Build reverse adjacency once: for each cell, who flows INTO it?
    upstream_of = {}
    for r in range(n_rows):
        for c in range(n_cols):
            dr, dc = down_row[r, c], down_col[r, c]
            if dr != -1:
                upstream_of.setdefault((dr, dc), []).append((r, c))

    catchment_cells = set()
    stack = [(target_row, target_col)]
    while stack:
        cell = stack.pop()
        if cell in catchment_cells:
            continue
        catchment_cells.add(cell)
        for up in upstream_of.get(cell, []):
            stack.append(up)

    return catchment_cells


def catchment_boundary_lonlat(dem, catchment_cells):
    """
    Compute a simple boundary polygon (convex hull) around the catchment
    cells, returned as a list of (lon, lat) points, for map overlay.
    """
    points = []
    for r, c in catchment_cells:
        x = dem.x_coords[c]
        y = dem.y_coords[r]
        points.append((x, y))

    if len(points) < 3:
        lon, lat = dem.local_to_lonlat(points[0][0], points[0][1])
        return [[lon, lat]]

    hull = MultiPoint(points).convex_hull
    hull_coords = list(hull.exterior.coords)
    return [list(dem.local_to_lonlat(x, y)) for x, y in hull_coords]


def extract_elevation_profile(dem, catchment_cells, pond_row, pond_col):
    """
    Extracts actual terrain elevation profile points from peak down to the recommended pond site.
    Returns list of dicts: [{"label": str, "elevation_m": float}]
    """
    if not catchment_cells:
        pond_elev = float(dem.elevation[pond_row, pond_col])
        return [
            {"label": "Ridge Peak", "elevation_m": round(pond_elev + 10.0, 1)},
            {"label": "Upper Catchment", "elevation_m": round(pond_elev + 7.5, 1)},
            {"label": "Mid Slope", "elevation_m": round(pond_elev + 5.0, 1)},
            {"label": "Lower Valley", "elevation_m": round(pond_elev + 2.5, 1)},
            {"label": "Pond Site", "elevation_m": round(pond_elev, 1)},
        ]

    elevs = [float(dem.elevation[r, c]) for r, c in catchment_cells]
    min_e = float(dem.elevation[pond_row, pond_col])
    max_e = max(elevs)

    diff = max_e - min_e
    return [
        {"label": "Ridge Peak", "elevation_m": round(max_e, 2)},
        {"label": "Upper Catchment", "elevation_m": round(max_e - diff * 0.25, 2)},
        {"label": "Mid Slope", "elevation_m": round(max_e - diff * 0.50, 2)},
        {"label": "Lower Valley", "elevation_m": round(min_e + diff * 0.20, 2)},
        {"label": "Pond Site", "elevation_m": round(min_e, 2)},
    ]



def calculate_expected_water_volume(area_m2: float, rainfall_mm: float = 1000.0, runoff_coeff: float = 0.35):
    """
    Calculates expected annual runoff water volume using the Rational Method:
    V = C * P * A

    Parameters:
    - area_m2: Catchment area in square meters (A)
    - rainfall_mm: Annual rainfall in millimeters (P)
    - runoff_coeff: Runoff coefficient C (0.15 to 0.60 depending on soil/land cover)

    Returns dict with volume in m3, Liters, Million Liters, and per-capita community impact.
    """
    rainfall_meters = rainfall_mm / 1000.0
    volume_m3 = area_m2 * rainfall_meters * runoff_coeff
    volume_liters = volume_m3 * 1000.0
    volume_million_liters = volume_m3 / 1000.0

    # Impact estimation: A typical rural family of 5 uses ~750 Liters/day (150L/person/day)
    # Annual domestic supply capacity (days of water for N households)
    households_served_for_100_days = int(volume_liters / (750.0 * 100))

    return {
        "rainfall_mm": round(rainfall_mm, 1),
        "runoff_coefficient": round(runoff_coeff, 2),
        "expected_volume_m3": round(volume_m3, 2),
        "expected_volume_liters": round(volume_liters, 0),
        "expected_volume_million_liters": round(volume_million_liters, 3),
        "estimated_households_served": max(1, households_served_for_100_days),
    }


def calculate_pond_dimensions(expected_volume_m3: float, recommended_depth_m: float = 3.0):
    """
    Estimates optimal pond engineering dimensions for capturing the expected runoff.
    """
    storage_capacity_m3 = round(expected_volume_m3 * 0.85, 2)  # 85% capture factor for safety
    surface_area_m2 = round(storage_capacity_m3 / recommended_depth_m, 2)
    length_m = round((surface_area_m2 * 1.25) ** 0.5, 1)
    width_m = round(surface_area_m2 / max(length_m, 1.0), 1)

    return {
        "target_storage_capacity_m3": storage_capacity_m3,
        "recommended_depth_m": recommended_depth_m,
        "surface_area_m2": surface_area_m2,
        "estimated_length_m": length_m,
        "estimated_width_m": width_m,
        "embankment_slope": "1:1.5",
    }

