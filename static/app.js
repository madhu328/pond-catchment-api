/**
 * JalDrishti — AI Village Pond & Catchment Hydrology Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // --------------------------------------------------------------------------
    // State Variables
    // --------------------------------------------------------------------------
    let map = null;
    let baseLayers = {};
    let drawnItems = null;
    let currentDrawnPolygon = null; // [[lon, lat], ...]
    let activeAnalysisData = null;
    let selectedKmlFile = null;

    let pondMarker = null;
    let catchmentPolygonLayer = null;
    let selectedLandPolygonLayer = null;

    let elevationChart = null;
    let hydrographChart = null;

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

        showToast('Map initialized. Draw land polygon or pick a preset.', 'info');
    }

    // --------------------------------------------------------------------------
    // UI Event Handlers
    // --------------------------------------------------------------------------
    function initUI() {
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

                const res = await fetch('/analyzeContour', {
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

                const res = await fetch('/analyzeSelectedArea', {
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
    // Map Overlays Rendering
    // --------------------------------------------------------------------------
    function renderResultsOnMap(data) {
        // Clear existing map layers
        if (pondMarker) map.removeLayer(pondMarker);
        if (catchmentPolygonLayer) map.removeLayer(catchmentPolygonLayer);

        const pond = data.recommended_pond_location;
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

            map.fitBounds(catchmentPolygonLayer.getBounds(), { padding: [50, 50] });
        }

        // 2. Render Suggested Pond Location Pin Marker with Glowing Ring
        const customIcon = L.divIcon({
            className: 'custom-pond-marker',
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });

        pondMarker = L.marker([pond.latitude, pond.longitude], { icon: customIcon }).addTo(map);

        const vol = data.expected_water_volume;
        pondMarker.bindPopup(`
            <div style="font-family: sans-serif; font-size: 13px; color: #0f172a; line-height: 1.5; padding: 4px;">
                <h4 style="color: #0284c7; margin: 0 0 6px 0; font-size: 14px;"><i class="fa-solid fa-location-dot"></i> Recommended Pond Site</h4>
                <strong>Coordinates:</strong> ${pond.latitude.toFixed(4)}° N, ${pond.longitude.toFixed(4)}° E<br>
                <strong>Elevation:</strong> ${pond.elevation_m} meters<br>
                <strong>Catchment Area:</strong> ${catchment.area_hectares} ha<br>
                <hr style="margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;">
                <strong style="color: #0369a1;">Expected Water Volume:</strong><br>
                <span style="font-size: 15px; font-weight: bold; color: #0284c7;">${vol.expected_volume_m3.toLocaleString()} m³</span> (${vol.expected_volume_million_liters} ML)
            </div>
        `).openPopup();
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

        document.getElementById('resPondCoords').textContent = `${pond.latitude.toFixed(4)}° N, ${pond.longitude.toFixed(4)}° E`;
        document.getElementById('resPondElevation').innerHTML = `<i class="fa-solid fa-arrow-trend-down text-cyan"></i> Elevation: ${pond.elevation_m} m (Natural Drainage Sink)`;

        document.getElementById('resCatchmentAreaHa').textContent = `${catchment.area_hectares} ha`;
        document.getElementById('resCatchmentAreaM2').textContent = catchment.area_m2.toLocaleString();
        document.getElementById('resContributingCells').textContent = `${catchment.num_contributing_cells} DEM cells (${catchment.elevation_min_m}m - ${catchment.elevation_max_m}m elev)`;

        document.getElementById('resVolumeM3').textContent = `${vol.expected_volume_m3.toLocaleString()} m³`;
        document.getElementById('resVolumeML').textContent = vol.expected_volume_million_liters;
        document.getElementById('resVolumeLiters').textContent = `${vol.expected_volume_liters.toLocaleString()} Liters Total Harvestable`;

        document.getElementById('resHouseholdsServed').textContent = `${vol.estimated_households_served} Rural Households`;

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
        const midE = (minE + maxE) / 2;

        // 1. Elevation Profile Chart
        const ctxElev = document.getElementById('elevationChart').getContext('2d');
        if (elevationChart) elevationChart.destroy();

        elevationChart = new Chart(ctxElev, {
            type: 'line',
            data: {
                labels: ['Ridge Peak', 'Upper Catchment', 'Mid Slope', 'Lower Valley', 'Pond Site'],
                datasets: [{
                    label: 'Elevation Profile (m)',
                    data: [maxE, maxE - (maxE - minE)*0.25, midE, minE + (maxE - minE)*0.15, minE],
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

    // Initialize Map and UI
    initMap();
    initUI();
});
