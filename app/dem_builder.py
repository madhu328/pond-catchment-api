"""
dem_builder.py
--------------
Turns a list of contour lines (each with an elevation value) into a
regular elevation grid (a simple DEM - Digital Elevation Model), which
is what the catchment analysis needs.

Approach:
1. Every point along every contour line is a known (x, y, z) sample,
   since we know the line's elevation and the point's lon/lat.
2. Convert lon/lat to a local metric coordinate system (meters), so
   distances and areas make physical sense.
3. Feed all these scattered (x, y, z) points into a grid interpolator
   (scipy.interpolate.griddata) to get elevation values on a regular
   grid at a chosen resolution (default 10m cells).
"""

import math
import numpy as np
from scipy.interpolate import griddata


class DEM:
    """Simple container for a regular-grid Digital Elevation Model."""

    def __init__(self, elevation, x_coords, y_coords, cell_size,
                 origin_lon, origin_lat, m_per_deg_lon, m_per_deg_lat):
        self.elevation = elevation      # 2D numpy array [row, col] -> meters
        self.x_coords = x_coords        # 1D array of x (meters, local)
        self.y_coords = y_coords        # 1D array of y (meters, local)
        self.cell_size = cell_size      # meters per grid cell
        self.origin_lon = origin_lon
        self.origin_lat = origin_lat
        self.m_per_deg_lon = m_per_deg_lon
        self.m_per_deg_lat = m_per_deg_lat

    def local_to_lonlat(self, x, y):
        """Convert local meter coordinates back to lon/lat for the response."""
        lon = self.origin_lon + x / self.m_per_deg_lon
        lat = self.origin_lat + y / self.m_per_deg_lat
        return lon, lat


def build_dem(contours: list[dict], cell_size: float = 10.0, max_grid_cells: int = 90000) -> DEM:
    """
    Build a regular-grid DEM from a list of contour lines.

    cell_size: target grid resolution in meters. Automatically coarsened
    if the contour map covers a very large area, to keep computation fast.
    """
    all_lons = []
    all_lats = []
    all_elevs = []

    for c in contours:
        elev = c["elevation"]
        for lon, lat in c["coords"]:
            all_lons.append(lon)
            all_lats.append(lat)
            all_elevs.append(elev)

    all_lons = np.array(all_lons)
    all_lats = np.array(all_lats)
    all_elevs = np.array(all_elevs)

    # Local projection: flatten lon/lat to meters around the map's center latitude.
    # This is accurate enough for village-scale areas (a few km across).
    origin_lon = all_lons.min()
    origin_lat = all_lats.min()
    center_lat = (all_lats.min() + all_lats.max()) / 2

    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(center_lat))

    x = (all_lons - origin_lon) * m_per_deg_lon
    y = (all_lats - origin_lat) * m_per_deg_lat

    width_m = x.max() - x.min()
    height_m = y.max() - y.min()

    # Auto-coarsen grid resolution if the area is large, so we never build
    # an unreasonably huge grid (keeps this generalizable to bigger maps).
    n_cols_est = width_m / cell_size
    n_rows_est = height_m / cell_size
    if n_cols_est * n_rows_est > max_grid_cells:
        scale = math.sqrt((n_cols_est * n_rows_est) / max_grid_cells)
        cell_size = cell_size * scale

    n_cols = max(int(width_m / cell_size), 2)
    n_rows = max(int(height_m / cell_size), 2)

    grid_x = np.linspace(x.min(), x.max(), n_cols)
    grid_y = np.linspace(y.min(), y.max(), n_rows)
    gx, gy = np.meshgrid(grid_x, grid_y)

    # Interpolate scattered contour points onto the regular grid.
    elevation = griddata(
        points=np.column_stack([x, y]),
        values=all_elevs,
        xi=(gx, gy),
        method="linear",
    )

    # Any grid cells outside the convex hull of the contour data come back
    # as NaN - fill those using nearest-neighbour so the grid is complete.
    if np.isnan(elevation).any():
        nearest = griddata(
            points=np.column_stack([x, y]),
            values=all_elevs,
            xi=(gx, gy),
            method="nearest",
        )
        elevation = np.where(np.isnan(elevation), nearest, elevation)

    return DEM(
        elevation=elevation,
        x_coords=grid_x,
        y_coords=grid_y,
        cell_size=cell_size,
        origin_lon=origin_lon,
        origin_lat=origin_lat,
        m_per_deg_lon=m_per_deg_lon,
        m_per_deg_lat=m_per_deg_lat,
    )
