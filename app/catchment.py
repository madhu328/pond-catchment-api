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
    Pick the recommended pond location: the cell where the most water
    naturally converges (highest flow accumulation), while ignoring the
    outer edge of the grid (edge cells are unreliable - water may just
    be flowing off the mapped area, not converging naturally).
    """
    n_rows, n_cols = dem.elevation.shape
    masked = acc.copy()
    masked[:edge_margin, :] = -1
    masked[-edge_margin:, :] = -1
    masked[:, :edge_margin] = -1
    masked[:, -edge_margin:] = -1

    idx = np.unravel_index(np.argmax(masked), masked.shape)
    return idx  # (row, col)


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
