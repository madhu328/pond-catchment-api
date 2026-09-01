"""
kml_parser.py
--------------
Reads a contour map file (.kml or .kmz) and extracts every contour line
along with the elevation value attached to it.

A contour KML (as exported by tools like the "Contour Map Generator")
stores each contour line as a <Placemark> containing a <LineString>.
The elevation of that particular line is usually stored in the
Placemark's <name> tag (e.g. "277.0").

Output format:
    [
        {"elevation": 277.0, "coords": [(lon, lat), (lon, lat), ...]},
        {"elevation": 278.0, "coords": [(lon, lat), ...]},
        ...
    ]
"""

import io
import zipfile
from lxml import etree

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def _parse_kml_bytes(kml_bytes: bytes) -> list[dict]:
    """Parse raw KML bytes and return a list of contour line dicts."""
    tree = etree.parse(io.BytesIO(kml_bytes))
    root = tree.getroot()

    placemarks = root.findall(".//kml:Placemark", KML_NS)

    contours = []
    for pm in placemarks:
        line = pm.find("kml:LineString", KML_NS)
        if line is None:
            # Skip label points / anything that is not an actual contour line
            continue

        coords_el = line.find("kml:coordinates", KML_NS)
        if coords_el is None or not coords_el.text:
            continue

        # Elevation is stored as the Placemark name, e.g. "277.0"
        name_el = pm.find("kml:name", KML_NS)
        elevation = None
        if name_el is not None and name_el.text:
            try:
                elevation = float(name_el.text.strip())
            except ValueError:
                elevation = None

        if elevation is None:
            # Fallback: some generators store it inside ExtendedData
            ext = pm.find(".//kml:SimpleData", KML_NS)
            if ext is not None and ext.text:
                try:
                    elevation = float(ext.text.strip())
                except ValueError:
                    continue
            else:
                continue

        coords = []
        for pair in coords_el.text.strip().split():
            parts = pair.split(",")
            if len(parts) < 2:
                continue
            lon, lat = float(parts[0]), float(parts[1])
            coords.append((lon, lat))

        if len(coords) >= 2:
            contours.append({"elevation": elevation, "coords": coords})

    return contours


def parse_contour_file(filename: str, file_bytes: bytes) -> list[dict]:
    """
    Entry point used by the API layer.
    Handles both plain .kml files and zipped .kmz files.
    """
    if filename.lower().endswith(".kmz"):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            # A KMZ is just a zip that contains one main .kml (usually doc.kml)
            kml_name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
            kml_bytes = z.read(kml_name)
    else:
        kml_bytes = file_bytes

    contours = _parse_kml_bytes(kml_bytes)

    if not contours:
        raise ValueError(
            "No usable contour lines with elevation values were found in this file."
        )

    return contours
