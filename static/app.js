/**
 * JalDrishti — AI Village Pond & Catchment Hydrology Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // --------------------------------------------------------------------------
    // State Variables
    // --------------------------------------------------------------------------
    let map = null;
    let baseLayers = {};
    let currentDrawnPolygon = null; // [[lon, lat], ...]
    let activeAnalysisData = null;
    let selectedKmlFile = null;

    let pondMarkers = [];
    let catchmentPolygonLayer = null;
    let selectedLandPolygonLayer = null;
    let clickInspectMarker = null;

    let elevationChart = null;
    let hydrographChart = null;

    // Dynamic Backend API Endpoint Resolution (Backend API on port 3313, Frontend UI on port 6313)
    function getApiBaseUrl() {
        const port = window.location.port;
        const host = window.location.hostname;
        const protocol = window.location.protocol;
        
        if (port === '6313' || port === '6000') {
            return `${protocol}//${host}:3313`;
        }
        if (port === '3313') {
            return '';
        }
        if (host === '10.1.75.51' || host === 'localhost' || host === '127.0.0.1') {
            return `${protocol}//${host}:3313`;
        }
        return '';
    }
    const API_BASE_URL = getApiBaseUrl();

    // --------------------------------------------------------------------------
    // Initialize Leaflet Interactive Map
    // --------------------------------------------------------------------------
    function initMap() {
        // Centered around Raipur / Durg Chhattisgarh sample region
        const defaultCenter = [21.2461, 81.2893];
        const defaultZoom = 14;

        map = L.map('map', {
            center: defaultCenter,
            zoom: defaultZoom,
            zoomControl: false
        });

        // Add zoom control top right
        L.control.zoom({ position: 'topright' }).addTo(map);

        // Basemap Layers
        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri World Imagery',
            maxZoom: 19
        });

        const topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: 'OpenTopoMap',
            maxZoom: 17
        });

        const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CartoDB Dark Matter',
            maxZoom: 19
        });

        const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        });

        baseLayers = {
            satellite: satelliteLayer,
            topo: topoLayer,
            dark: darkLayer,
            streets: streetLayer
        };

        // Set default satellite basemap
        satelliteLayer.addTo(map);

        // Initialize Leaflet Geoman Drawing Controls
        map.pm.addControls({
            position: 'topleft',
            drawPolygon: true,
            drawRectangle: true,
            drawCircleMarker: false,
            drawCircle: false,
            drawPolyline: false,
            drawMarker: false,
            editMode: true,
            dragMode: false,
            cutPolygon: false,
            removalMode: true
        });

        // Handle drawn polygons
        map.on('pm:create', (e) => {
            const layer = e.layer;
            if (selectedLandPolygonLayer) {
                map.removeLayer(selectedLandPolygonLayer);
            }
            selectedLandPolygonLayer = layer;

            // Extract coordinates
            const latlngs = layer.getLatLngs()[0];
            currentDrawnPolygon = latlngs.map(pt => [pt.lng, pt.lat]);
            // Close polygon loop if needed
            if (currentDrawnPolygon[0][0] !== currentDrawnPolygon[currentDrawnPolygon.length - 1][0]) {
                currentDrawnPolygon.push([...currentDrawnPolygon[0]]);
            }

            updateDrawStatus(true, currentDrawnPolygon.length - 1);
            showToast('Land area polygon captured! Click "Run Catchment Analysis" to analyze.', 'success');
        });

        map.on('pm:remove', (e) => {
            currentDrawnPolygon = null;
            selectedLandPolygonLayer = null;
            updateDrawStatus(false);
        });

        // Live Cursor Coordinates Tracker
        map.on('mousemove', (e) => {
            const liveCoordDisplay = document.getElementById('liveCoordsDisplay');
            if (liveCoordDisplay) {
                liveCoordDisplay.innerHTML = `<i class="fa-solid fa-crosshairs text-cyan"></i> <strong>Live Pointer:</strong> Lat: ${e.latlng.lat.toFixed(6)}° N | Lon: ${e.latlng.lng.toFixed(6)}° E`;
            }
        });

        // Click on map to inspect coordinates
        map.on('click', (e) => {
            if (map.pm.globalDrawModeEnabled()) return;
            if (clickInspectMarker) map.removeLayer(clickInspectMarker);

            const clickIcon = L.divIcon({
                className: 'click-inspect-marker',
                html: `<div class="inspect-pin"><i class="fa-solid fa-location-dot"></i></div>`,
                iconSize: [30, 30],
                iconAnchor: [15, 30]
            });

            clickInspectMarker = L.marker(e.latlng, { icon: clickIcon }).addTo(map);
            clickInspectMarker.bindPopup(`
                <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; padding: 2px;">
                    <strong style="color: #0284c7;"><i class="fa-solid fa-map-pin"></i> Inspected Map Point</strong><br>
                    <strong>Latitude:</strong> ${e.latlng.lat.toFixed(6)}° N<br>
                    <strong>Longitude:</strong> ${e.latlng.lng.toFixed(6)}° E
                </div>
            `).openPopup();
        });

        showToast('Map initialized. Auto-generating terrain flow analysis...', 'info');
    }

    // --------------------------------------------------------------------------
    // UI Event Handlers
    // --------------------------------------------------------------------------
    function initUI() {
        // Header Presets Button Quick Link
        const btnPresetsHeader = document.getElementById('btnPresets');
        if (btnPresetsHeader) {
            btnPresetsHeader.addEventListener('click', () => {
                const presetTabBtn = document.querySelector('.tab-btn[data-tab="presetMode"]');
                if (presetTabBtn) presetTabBtn.click();
                const drawer = document.getElementById('leftDrawer');
                if (drawer) drawer.style.transform = 'translateX(0)';
            });
        }

        // Tab Switcher
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

                btn.classList.add('active');
                const targetTab = btn.getAttribute('data-tab');
                document.getElementById(targetTab).classList.add('active');
            });
        });


        // Basemap Switcher Buttons
        document.querySelectorAll('.basemap-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.basemap-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const layerKey = btn.getAttribute('data-layer');
                Object.values(baseLayers).forEach(layer => map.removeLayer(layer));
                if (baseLayers[layerKey]) {
                    baseLayers[layerKey].addTo(map);
                }
            });
        });

        // File Upload Handlers
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('kmlFileInput');
        const browseBtn = document.getElementById('browseFileBtn');

        browseBtn.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('click', (e) => {
            if (e.target !== browseBtn) fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            if (fileInput.files.length > 0) {
                handleFileSelect(fileInput.files[0]);
            }
        });

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#38bdf8';
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.style.borderColor = 'rgba(255, 255, 255, 0.08)';
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = 'rgba(255, 255, 255, 0.08)';
            if (e.dataTransfer.files.length > 0) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        // Presets Selector
        document.querySelectorAll('.preset-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');

                const presetType = card.getAttribute('data-preset');
                loadPreset(presetType);
            });
        });

        // Parameter Sliders Realtime Updates
        const rainfallRange = document.getElementById('rainfallRange');
        const rainfallVal = document.getElementById('rainfallValue');
        rainfallRange.addEventListener('input', (e) => {
            rainfallVal.textContent = `${e.target.value} mm`;
            recalculateHydrology();
        });

        document.querySelectorAll('.preset-pills .pill-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.preset-pills .pill-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const val = btn.getAttribute('data-val');
                rainfallRange.value = val;
                rainfallVal.textContent = `${val} mm`;
                recalculateHydrology();
            });
        });

        const runoffSelect = document.getElementById('runoffCoeffSelect');
        const runoffVal = document.getElementById('runoffCoeffValue');
        runoffSelect.addEventListener('change', (e) => {
            runoffVal.textContent = `C = ${e.target.value}`;
            recalculateHydrology();
        });

        const depthRange = document.getElementById('depthRange');
        const depthVal = document.getElementById('depthValue');
        depthRange.addEventListener('input', (e) => {
            depthVal.textContent = `${e.target.value} m`;
            recalculateHydrology();
        });

        // Analyze Action Button
        document.getElementById('btnAnalyze').addEventListener('click', runAnalysis);

        // Sidebar Toggle Drawers
        document.getElementById('toggleLeftDrawer').addEventListener('click', () => {
            const drawer = document.getElementById('leftDrawer');
            drawer.style.transform = drawer.style.transform === 'translateX(-100%)' ? 'translateX(0)' : 'translateX(-100%)';
        });

        document.getElementById('toggleRightDrawer').addEventListener('click', () => {
            const drawer = document.getElementById('rightDrawer');
            drawer.style.transform = drawer.style.transform === 'translateX(100%)' ? 'translateX(0)' : 'translateX(100%)';
        });

        // Export GeoJSON
        document.getElementById('btnExportGeoJSON').addEventListener('click', exportGeoJSON);
    }

    // --------------------------------------------------------------------------
    // File & Preset Helpers
    // --------------------------------------------------------------------------
    function handleFileSelect(file) {
        selectedKmlFile = file;
        document.getElementById('uploadedFileName').textContent = file.name;
        document.getElementById('fileNameDisplay').style.display = 'block';
        showToast(`Loaded ${file.name}. Ready for catchment analysis.`, 'success');
    }

    function loadPreset(presetType) {
        if (presetType === 'raipur') {
            selectedKmlFile = null;
            currentDrawnPolygon = [
                [81.2850, 21.2430],
                [81.2930, 21.2430],
                [81.2930, 21.2490],
                [81.2850, 21.2490],
                [81.2850, 21.2430]
            ];
            map.flyTo([21.2461, 81.2893], 15);
            showToast('Preset Loaded: Raipur Basin Contour Region (8.5 km²)', 'info');
        } else if (presetType === 'durg') {
            selectedKmlFile = null;
            currentDrawnPolygon = [
                [81.2800, 21.1880],
                [81.2880, 21.1880],
                [81.2880, 21.1940],
                [81.2800, 21.1940],
                [81.2800, 21.1880]
            ];
            map.flyTo([21.1910, 81.2840], 15);
            showToast('Preset Loaded: Durg Rural Agricultural Watershed', 'info');
        } else if (presetType === 'hilly') {
            selectedKmlFile = null;
            currentDrawnPolygon = [
                [81.3080, 21.2620],
                [81.3160, 21.2620],
                [81.3160, 21.2680],
                [81.3080, 21.2680],
                [81.3080, 21.2620]
            ];
            map.flyTo([21.2650, 81.3120], 15);
            showToast('Preset Loaded: Micro-Hilly Catchment Region', 'info');
        }
        updateDrawStatus(true, 4);
        runAnalysis();
    }

    function updateDrawStatus(hasPolygon, vertexCount = 0) {
        const box = document.getElementById('drawStatusBox');
        if (hasPolygon) {
            box.classList.add('selected');
            box.innerHTML = `
                <span class="status-icon text-emerald"><i class="fa-solid fa-circle-check"></i></span>
                <div class="status-info">
                    <h4>Land Polygon Selected</h4>
                    <p>${vertexCount} boundary vertices defined on map.</p>
                </div>
            `;
        } else {
            box.classList.remove('selected');
            box.innerHTML = `
                <span class="status-icon text-amber"><i class="fa-solid fa-triangle-exclamation"></i></span>
                <div class="status-info">
                    <h4>No Area Selected</h4>
                    <p>Draw a polygon or select a preset to analyze catchment.</p>
                </div>
            `;
        }
    }

    // --------------------------------------------------------------------------
    // Core Analysis API Call
    // --------------------------------------------------------------------------
    async function runAnalysis() {
        const activeTab = document.querySelector('.tab-btn.active').getAttribute('data-tab');
        const rainfall = parseFloat(document.getElementById('rainfallRange').value);
        const runoff = parseFloat(document.getElementById('runoffCoeffSelect').value);

        showToast('Processing terrain D8 flow direction & accumulation...', 'loading');

        try {
            let responseData = null;

            if (activeTab === 'uploadMode' && selectedKmlFile) {
                // Upload KML file
                const formData = new FormData();
                formData.append('contour_map', selectedKmlFile);
                formData.append('rainfall_mm', rainfall);
                formData.append('runoff_coefficient', runoff);

                const res = await fetch(`${API_BASE_URL}/analyzeContour`, {
                    method: 'POST',
                    body: formData
                });
                if (!res.ok) throw new Error(await res.text());
                responseData = await res.json();
            } else {
                // Interactive Polygon or Preset Polygon
                const poly = currentDrawnPolygon || [
                    [81.2850, 21.2430],
                    [81.2930, 21.2430],
                    [81.2930, 21.2490],
                    [81.2850, 21.2490],
                    [81.2850, 21.2430]
                ];

                const payload = {
                    polygon_lonlat: poly,
                    rainfall_mm: rainfall,
                    runoff_coefficient: runoff
                };

                const res = await fetch(`${API_BASE_URL}/analyzeSelectedArea`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error(await res.text());
                responseData = await res.json();
            }

            activeAnalysisData = responseData;
            renderResultsOnMap(responseData);
            displayResultsDashboard(responseData);
            showToast('Catchment analysis completed successfully!', 'success');
            document.getElementById('btnExportGeoJSON').disabled = false;

        } catch (err) {
            console.error('Analysis Error:', err);
            showToast(`Analysis failed: ${err.message}`, 'error');
        }
    }

    // --------------------------------------------------------------------------
    // Map Overlays & Live Pointer Rendering
    // --------------------------------------------------------------------------
    function renderResultsOnMap(data) {
        // Clear existing map layers & markers
        if (pondMarkers && pondMarkers.length > 0) {
            pondMarkers.forEach(m => map.removeLayer(m));
        }
        pondMarkers = [];

        if (catchmentPolygonLayer) map.removeLayer(catchmentPolygonLayer);

        const primaryPond = data.recommended_pond_location;
        const catchment = data.catchment;

        // 1. Render Catchment Boundary Polygon
        if (catchment.boundary_polygon_lonlat && catchment.boundary_polygon_lonlat.length > 0) {
            // lon/lat to lat/lon for Leaflet
            const leafletCoords = catchment.boundary_polygon_lonlat.map(pt => [pt[1], pt[0]]);
            
            catchmentPolygonLayer = L.polygon(leafletCoords, {
                color: '#38bdf8',
                weight: 2.5,
                opacity: 0.9,
                fillColor: '#38bdf8',
                fillOpacity: 0.25,
                dashArray: '6, 6'
            }).addTo(map);

            catchmentPolygonLayer.bindTooltip(`
                <div style="font-family: sans-serif; font-size: 12px; color: #0f172a;">
                    <strong>🌊 Catchment Area</strong><br>
                    Area: <strong>${catchment.area_hectares} ha</strong> (${catchment.area_m2.toLocaleString()} m²)<br>
                    Grid Cells: <strong>${catchment.num_contributing_cells}</strong>
                </div>
            `);

            map.fitBounds(catchmentPolygonLayer.getBounds(), { padding: [60, 60] });
        }

        // 2. Render Live Pulsing Pond Pointer Markers + Lat/Lon Badges for ALL identified pond sites
        const ponds = (data.all_ponds && data.all_ponds.length > 0) ? data.all_ponds : [{
            rank: 1,
            type: "Primary Storage Pond",
            badge: "PRIMARY POND",
            color: "#38bdf8",
            latitude: primaryPond.latitude,
            longitude: primaryPond.longitude,
            elevation_m: primaryPond.elevation_m,
            expected_water_volume: data.expected_water_volume,
            catchment_area_ha: catchment.area_hectares,
            catchment_area_m2: catchment.area_m2
        }];

        ponds.forEach((p, idx) => {
            const pColor = p.color || '#38bdf8';
            const badgeTitle = p.badge || `POND SITE #${p.rank || idx + 1}`;
            const coordBadgeText = `${badgeTitle}: ${p.latitude.toFixed(6)}° N, ${p.longitude.toFixed(6)}° E`;

            const customIcon = L.divIcon({
                className: `custom-pond-marker-wrapper rank-${p.rank || 1}`,
                html: `
                    <div class="pond-beacon-ring" style="border-color: ${pColor};"></div>
                    <div class="pond-beacon-pulse" style="background: ${pColor}; opacity: 0.5;"></div>
                    <div class="pond-marker-pin" style="background: linear-gradient(135deg, ${pColor}, #0284c7); box-shadow: 0 0 20px ${pColor};">
                        <i class="fa-solid ${p.rank === 1 ? 'fa-droplet' : (p.rank === 2 ? 'fa-filter' : 'fa-water')}"></i>
                    </div>
                    <div class="pond-live-coord-badge" style="border-color: ${pColor}; color: ${pColor};">
                        <i class="fa-solid fa-location-dot"></i> ${coordBadgeText}
                    </div>
                `,
                iconSize: [280, 80],
                iconAnchor: [140, 22]
            });

            const m = L.marker([p.latitude, p.longitude], { icon: customIcon }).addTo(map);

            const vol = p.expected_water_volume || data.expected_water_volume;
            const catchmentAreaHa = p.catchment_area_ha || catchment.area_hectares;
            const catchmentAreaM2 = p.catchment_area_m2 || catchment.area_m2;

            const popupContent = `
                <div class="live-pond-popup">
                    <div class="popup-header">
                        <i class="fa-solid fa-location-dot" style="color: ${pColor};"></i>
                        <h4 style="color: ${pColor};">${(p.type || 'SUGGESTED POND LOCATION').toUpperCase()}</h4>
                    </div>
                    <div class="popup-coords-badge" style="border: 1px solid ${pColor};">
                        <span class="coord-item"><strong>LAT:</strong> ${p.latitude.toFixed(6)}° N</span>
                        <span class="coord-item"><strong>LON:</strong> ${p.longitude.toFixed(6)}° E</span>
                    </div>
                    <div class="popup-body">
                        <div class="popup-row">
                            <span>Site Designation:</span>
                            <strong style="color: ${pColor};">${p.type || 'Primary Pond'}</strong>
                        </div>
                        <div class="popup-row">
                            <span>Terrain Elevation:</span>
                            <strong>${p.elevation_m} meters</strong>
                        </div>
                        <div class="popup-row">
                            <span>Catchment Basin:</span>
                            <strong>${catchmentAreaHa} ha (${catchmentAreaM2.toLocaleString()} m²)</strong>
                        </div>
                        <div class="popup-divider"></div>
                        <div class="popup-highlight" style="border-left-color: ${pColor};">
                            <span>Expected Harvestable Volume:</span>
                            <strong class="vol-text" style="color: ${pColor};">${vol.expected_volume_m3.toLocaleString()} m³ (${vol.expected_volume_million_liters} ML)</strong>
                        </div>
                    </div>
                </div>
            `;

            m.bindPopup(popupContent, { maxWidth: 320, className: 'custom-leaflet-popup' });
            if (p.rank === 1) m.openPopup();
            pondMarkers.push(m);
        });
    }

    // --------------------------------------------------------------------------
    // Results Dashboard & Calculations Display
    // --------------------------------------------------------------------------
    function displayResultsDashboard(data) {
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('resultsDashboard').style.display = 'block';

        const pond = data.recommended_pond_location;
        const catchment = data.catchment;
        const vol = data.expected_water_volume;
        const dims = data.recommended_pond_dimensions;

        document.getElementById('resPondCoords').textContent = `${pond.latitude.toFixed(6)}° N, ${pond.longitude.toFixed(6)}° E`;
        document.getElementById('resPondElevation').innerHTML = `<i class="fa-solid fa-arrow-trend-down text-cyan"></i> Elevation: ${pond.elevation_m} m (Natural Drainage Sink)`;

        document.getElementById('resCatchmentAreaHa').textContent = `${catchment.area_hectares} ha`;
        document.getElementById('resCatchmentAreaM2').textContent = catchment.area_m2.toLocaleString();
        document.getElementById('resContributingCells').textContent = `${catchment.num_contributing_cells} DEM cells (${catchment.elevation_min_m}m - ${catchment.elevation_max_m}m elev)`;

        document.getElementById('resVolumeM3').textContent = `${vol.expected_volume_m3.toLocaleString()} m³`;
        document.getElementById('resVolumeML').textContent = vol.expected_volume_million_liters;
        document.getElementById('resVolumeLiters').textContent = `${vol.expected_volume_liters.toLocaleString()} Liters Total Harvestable`;

        document.getElementById('resHouseholdsServed').textContent = `${vol.estimated_households_served} Rural Households`;

        // Render Identified Ponds List in Right Sidebar
        const pondCountBadge = document.getElementById('pondCountBadge');
        const pondsContainer = document.getElementById('allPondsListContainer');
        if (pondCountBadge && pondsContainer) {
            const ponds = (data.all_ponds && data.all_ponds.length > 0) ? data.all_ponds : [{
                rank: 1,
                type: "Primary Storage Pond",
                badge: "PRIMARY POND",
                color: "#38bdf8",
                latitude: pond.latitude,
                longitude: pond.longitude,
                elevation_m: pond.elevation_m,
                expected_water_volume: vol,
                catchment_area_ha: catchment.area_hectares,
                catchment_area_m2: catchment.area_m2
            }];

            pondCountBadge.textContent = ponds.length;
            pondsContainer.innerHTML = ponds.map((p, idx) => `
                <div class="pond-site-card" data-idx="${idx}" style="border-left: 3px solid ${p.color || '#38bdf8'};">
                    <div class="pond-card-header">
                        <span class="pond-card-title" style="color: ${p.color || '#38bdf8'};">
                            <i class="fa-solid ${p.rank === 1 ? 'fa-droplet' : (p.rank === 2 ? 'fa-filter' : 'fa-water')}"></i> ${p.type}
                        </span>
                        <span class="pond-card-rank">Rank #${p.rank || idx + 1}</span>
                    </div>
                    <div class="pond-card-coords">
                        <strong>Lat:</strong> ${p.latitude.toFixed(6)}° N | <strong>Lon:</strong> ${p.longitude.toFixed(6)}° E
                    </div>
                    <div class="pond-card-stats">
                        <span>Elev: <strong>${p.elevation_m}m</strong></span>
                        <span>Area: <strong>${p.catchment_area_ha || catchment.area_hectares} ha</strong></span>
                        <span>Vol: <strong>${(p.expected_water_volume ? p.expected_water_volume.expected_volume_m3 : vol.expected_volume_m3).toLocaleString()} m³</strong></span>
                    </div>
                </div>
            `).join('');

            // Add click listeners to focus map on clicked pond card
            document.querySelectorAll('.pond-site-card').forEach(card => {
                card.addEventListener('click', () => {
                    const idx = parseInt(card.getAttribute('data-idx'));
                    if (pondMarkers[idx] && ponds[idx]) {
                        const targetPond = ponds[idx];
                        map.flyTo([targetPond.latitude, targetPond.longitude], 17);
                        pondMarkers[idx].openPopup();
                    }
                });
            });
        }

        document.getElementById('specCapacity').textContent = `${dims.target_storage_capacity_m3.toLocaleString()} m³`;
        document.getElementById('specDepth').textContent = `${dims.recommended_depth_m} m`;
        document.getElementById('specArea').textContent = `${dims.surface_area_m2.toLocaleString()} m²`;
        document.getElementById('specDimensions').textContent = `${dims.estimated_length_m} m × ${dims.estimated_width_m} m`;

        renderCharts(data);
    }

    // --------------------------------------------------------------------------
    // Instant Realtime Parameter Recalculation
    // --------------------------------------------------------------------------
    function recalculateHydrology() {
        if (!activeAnalysisData) return;

        const rainfall = parseFloat(document.getElementById('rainfallRange').value);
        const runoffCoeff = parseFloat(document.getElementById('runoffCoeffSelect').value);
        const depth = parseFloat(document.getElementById('depthRange').value);

        const areaM2 = activeAnalysisData.catchment.area_m2;

        // Rational Method V = C * P * A
        const volumeM3 = areaM2 * (rainfall / 1000.0) * runoffCoeff;
        const volumeLiters = volumeM3 * 1000.0;
        const volumeML = volumeM3 / 1000.0;
        const households = Math.max(1, Math.floor(volumeLiters / (750.0 * 100)));

        const storageCapacityM3 = Math.round(volumeM3 * 0.85);
        const surfaceAreaM2 = Math.round(storageCapacityM3 / depth);
        const lengthM = Math.round(Math.sqrt(surfaceAreaM2 * 1.25) * 10) / 10;
        const widthM = Math.round((surfaceAreaM2 / Math.max(lengthM, 1.0)) * 10) / 10;

        // Update UI metrics
        document.getElementById('resVolumeM3').textContent = `${Math.round(volumeM3).toLocaleString()} m³`;
        document.getElementById('resVolumeML').textContent = (Math.round(volumeML * 100) / 100).toFixed(2);
        document.getElementById('resVolumeLiters').textContent = `${Math.round(volumeLiters).toLocaleString()} Liters Total Harvestable`;
        document.getElementById('resHouseholdsServed').textContent = `${households} Rural Households`;

        document.getElementById('specCapacity').textContent = `${storageCapacityM3.toLocaleString()} m³`;
        document.getElementById('specDepth').textContent = `${depth} m`;
        document.getElementById('specArea').textContent = `${surfaceAreaM2.toLocaleString()} m²`;
        document.getElementById('specDimensions').textContent = `${lengthM} m × ${widthM} m`;

        // Update active object
        activeAnalysisData.expected_water_volume = {
            rainfall_mm: rainfall,
            runoff_coefficient: runoffCoeff,
            expected_volume_m3: Math.round(volumeM3),
            expected_volume_liters: Math.round(volumeLiters),
            expected_volume_million_liters: (Math.round(volumeML * 100) / 100).toFixed(2),
            estimated_households_served: households
        };
    }

    // --------------------------------------------------------------------------
    // Chart.js Visualizations
    // --------------------------------------------------------------------------
    function renderCharts(data) {
        const catchment = data.catchment;
        const minE = catchment.elevation_min_m || 268;
        const maxE = catchment.elevation_max_m || 285;

        // Use real backend elevation profile if available
        let labels = ['Ridge Peak', 'Upper Catchment', 'Mid Slope', 'Lower Valley', 'Pond Site'];
        let profileValues = [maxE, maxE - (maxE - minE)*0.25, (minE + maxE)/2, minE + (maxE - minE)*0.15, minE];

        if (catchment.elevation_profile && Array.isArray(catchment.elevation_profile) && catchment.elevation_profile.length > 0) {
            labels = catchment.elevation_profile.map(p => p.label);
            profileValues = catchment.elevation_profile.map(p => p.elevation_m);
        }

        // 1. Elevation Profile Chart
        const ctxElev = document.getElementById('elevationChart').getContext('2d');
        if (elevationChart) elevationChart.destroy();

        elevationChart = new Chart(ctxElev, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Elevation Profile (m)',
                    data: profileValues,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.15)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#34d399'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    }
                }
            }
        });


        // 2. Hydrograph Chart
        const ctxHydro = document.getElementById('hydrographChart').getContext('2d');
        if (hydrographChart) hydrographChart.destroy();

        const annualVol = data.expected_water_volume.expected_volume_m3;
        // Typical monsoon monthly distribution %: Jun 15%, Jul 35%, Aug 30%, Sep 20%
        const monthlyVol = [0, 0, 0, 0, 0, annualVol * 0.15, annualVol * 0.35, annualVol * 0.30, annualVol * 0.20, 0, 0, 0];

        hydrographChart = new Chart(ctxHydro, {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [{
                    label: 'Monthly Water Harvested (m³)',
                    data: monthlyVol,
                    backgroundColor: 'rgba(56, 189, 248, 0.6)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    }
                }
            }
        });
    }

    // --------------------------------------------------------------------------
    // Export GeoJSON File Download
    // --------------------------------------------------------------------------
    function exportGeoJSON() {
        if (!activeAnalysisData) return;

        const pond = activeAnalysisData.recommended_pond_location;
        const catchment = activeAnalysisData.catchment;
        const vol = activeAnalysisData.expected_water_volume;

        const geojson = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: {
                        type: "Point",
                        coordinates: [pond.longitude, pond.latitude]
                    },
                    properties: {
                        name: "Suggested Pond Location",
                        latitude: pond.latitude,
                        longitude: pond.longitude,
                        elevation_m: pond.elevation_m,
                        expected_water_volume_m3: vol.expected_volume_m3,
                        expected_water_volume_liters: vol.expected_volume_liters
                    }
                },
                {
                    type: "Feature",
                    geometry: {
                        type: "Polygon",
                        coordinates: [catchment.boundary_polygon_lonlat]
                    },
                    properties: {
                        name: "Catchment Area Boundary",
                        area_m2: catchment.area_m2,
                        area_hectares: catchment.area_hectares,
                        num_contributing_cells: catchment.num_contributing_cells
                    }
                }
            ]
        };

        const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `jaldrishti_pond_catchment_${Date.now()}.geojson`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('GeoJSON exported successfully!', 'success');
    }

    // Toast Alert Helper
    function showToast(msg, type = 'info') {
        const toast = document.getElementById('mapToast');
        const icon = toast.querySelector('.toast-icon');
        const text = document.getElementById('toastMessage');

        text.textContent = msg;
        if (type === 'loading') {
            icon.className = 'fa-solid fa-spinner fa-spin toast-icon text-cyan';
        } else if (type === 'success') {
            icon.className = 'fa-solid fa-circle-check toast-icon text-emerald';
        } else if (type === 'error') {
            icon.className = 'fa-solid fa-circle-exclamation toast-icon text-rose';
        } else {
            icon.className = 'fa-solid fa-circle-info toast-icon text-cyan';
        }
    }

    // Initialize Map, UI, and Auto-Run Initial Terrain Analysis
    initMap();
    initUI();

    // Auto-run analysis on page load so pond marker pointer & catchment area are instantly visible
    setTimeout(() => {
        runAnalysis();
    }, 500);
});
