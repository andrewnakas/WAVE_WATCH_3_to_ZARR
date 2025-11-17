// Global state
let map;
let waveData = null;
let timeseriesData = null;
let currentVariable = 'swh';
let particleSystem = null;
let heatmapLayer = null;

// Color scales for different variables
const colorScales = {
    swh: { min: 0, max: 10, colors: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] },
    perpw: { min: 0, max: 20, colors: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] },
    dirpw: { min: 0, max: 360, colors: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] },
    shww: { min: 0, max: 8, colors: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] },
    shts: { min: 0, max: 8, colors: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] }
};

// Initialize the application
async function init() {
    // Initialize map
    map = L.map('map', {
        center: [0, 180],
        zoom: 3,
        minZoom: 2,
        maxZoom: 8
    });

    // Add base layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Load data
    await loadData();

    // Set up particle system
    particleSystem = new ParticleSystem();
    particleSystem.init();

    // Set up event listeners
    setupEventListeners();

    // Initial render
    updateVisualization();
}

// Load JSON data
async function loadData() {
    try {
        // Load summary first
        const summary = await fetch('data/summary.json').then(r => r.json());
        document.getElementById('run-info').textContent =
            `Run: ${new Date(summary.run_time).toUTCString()}`;

        // Load latest data
        waveData = await fetch('data/latest_data.json').then(r => r.json());
        console.log('Loaded wave data:', waveData);

        // Load timeseries data if available
        if (summary.data_files.timeseries) {
            timeseriesData = await fetch('data/timeseries_data.json').then(r => r.json());
            console.log('Loaded timeseries data:', timeseriesData);
        }

    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('run-info').textContent = 'Error loading data';
    }
}

// Set up event listeners
function setupEventListeners() {
    // Variable selection
    document.getElementById('variable-select').addEventListener('change', (e) => {
        currentVariable = e.target.value;
        updateVisualization();
    });

    // Particle controls
    document.getElementById('show-particles').addEventListener('change', (e) => {
        particleSystem.setEnabled(e.target.checked);
    });

    document.getElementById('particle-count').addEventListener('input', (e) => {
        particleSystem.setParticleCount(parseInt(e.target.value));
        document.getElementById('particle-count-label').textContent = e.target.value;
    });

    document.getElementById('particle-speed').addEventListener('input', (e) => {
        particleSystem.setSpeed(parseFloat(e.target.value));
        document.getElementById('particle-speed-label').textContent = e.target.value + 'x';
    });

    // Map click for forecast
    map.on('click', handleMapClick);

    // Window resize
    window.addEventListener('resize', () => {
        particleSystem.resize();
    });
}

// Update visualization
function updateVisualization() {
    if (!waveData) return;

    // Remove existing heatmap
    if (heatmapLayer) {
        map.removeLayer(heatmapLayer);
    }

    // Create heatmap points
    const points = [];
    const varData = waveData.variables[currentVariable];

    if (!varData) {
        console.error('Variable not found:', currentVariable);
        return;
    }

    for (let i = 0; i < waveData.latitude.length; i++) {
        for (let j = 0; j < waveData.longitude.length; j++) {
            const value = varData[i][j];
            if (value !== null && !isNaN(value)) {
                points.push({
                    lat: waveData.latitude[i],
                    lon: waveData.longitude[j],
                    value: value
                });
            }
        }
    }

    // Create colored markers
    const colorScale = colorScales[currentVariable];
    heatmapLayer = L.layerGroup();

    // Create a grid of colored rectangles
    const latStep = waveData.latitude[1] - waveData.latitude[0];
    const lonStep = waveData.longitude[1] - waveData.longitude[0];

    points.forEach(point => {
        const color = getColor(point.value, colorScale.min, colorScale.max, colorScale.colors);
        const bounds = [
            [point.lat - latStep/2, point.lon - lonStep/2],
            [point.lat + latStep/2, point.lon + lonStep/2]
        ];

        L.rectangle(bounds, {
            color: color,
            fillColor: color,
            fillOpacity: 0.6,
            weight: 0
        }).addTo(heatmapLayer);
    });

    heatmapLayer.addTo(map);

    // Update legend
    updateLegend(currentVariable);

    // Update particle system
    particleSystem.updateData(waveData, currentVariable);
}

// Get color for value
function getColor(value, min, max, colors) {
    const normalized = Math.max(0, Math.min(1, (value - min) / (max - min)));
    const index = Math.floor(normalized * (colors.length - 1));
    return colors[Math.min(index, colors.length - 1)];
}

// Update legend
function updateLegend(variable) {
    const variableNames = {
        swh: 'Significant Wave Height (m)',
        perpw: 'Wave Period (s)',
        dirpw: 'Wave Direction (°)',
        shww: 'Wind Wave Height (m)',
        shts: 'Swell Height (m)'
    };

    document.getElementById('legend-title').textContent = variableNames[variable];
    document.getElementById('legend-min').textContent = colorScales[variable].min;
    document.getElementById('legend-max').textContent = colorScales[variable].max;
}

// Handle map click
function handleMapClick(e) {
    if (!timeseriesData) {
        alert('Time series data not available (single timestep dataset)');
        return;
    }

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    // Find nearest grid point
    const latIdx = findNearestIndex(timeseriesData.latitude, lat);
    const lonIdx = findNearestIndex(timeseriesData.longitude, lon);

    if (latIdx === -1 || lonIdx === -1) {
        console.error('Grid point not found');
        return;
    }

    showForecast(lat, lon, latIdx, lonIdx);
}

// Find nearest index in array
function findNearestIndex(array, value) {
    let minDist = Infinity;
    let minIdx = -1;

    for (let i = 0; i < array.length; i++) {
        const dist = Math.abs(array[i] - value);
        if (dist < minDist) {
            minDist = dist;
            minIdx = i;
        }
    }

    return minIdx;
}

// Show forecast panel
function showForecast(lat, lon, latIdx, lonIdx) {
    const panel = document.getElementById('forecast-panel');
    panel.classList.add('active');

    // Extract time series for this point
    const swh = timeseriesData.variables.swh[latIdx][lonIdx];
    const perpw = timeseriesData.variables.perpw ? timeseriesData.variables.perpw[latIdx][lonIdx] : null;
    const dirpw = timeseriesData.variables.dirpw ? timeseriesData.variables.dirpw[latIdx][lonIdx] : null;

    // Calculate statistics
    const currentSwh = swh[0];
    const maxSwh = Math.max(...swh.filter(v => v !== null));
    const avgSwh = (swh.filter(v => v !== null).reduce((a,b) => a + b, 0) / swh.filter(v => v !== null).length).toFixed(2);

    const currentPeriod = perpw ? perpw[0] : null;
    const currentDirection = dirpw ? dirpw[0] : null;

    // Get direction string
    const directionStr = currentDirection !== null ? getDirectionString(currentDirection) : 'N/A';

    // Update location info with comprehensive data
    document.getElementById('location-info').innerHTML = `
        <div style="margin-bottom: 10px;">
            <strong>Location:</strong> ${lat.toFixed(2)}°${lat >= 0 ? 'N' : 'S'}, ${lon.toFixed(2)}°${lon >= 0 ? 'E' : 'W'}<br>
            <strong>Grid Point:</strong> ${timeseriesData.latitude[latIdx].toFixed(2)}°, ${timeseriesData.longitude[lonIdx].toFixed(2)}°
        </div>
        <div style="padding: 10px; background: #f5f5f5; border-radius: 4px; margin-bottom: 10px;">
            <div style="font-weight: bold; margin-bottom: 5px; color: #1e3c72;">Current Conditions</div>
            <table style="width: 100%; font-size: 13px;">
                <tr>
                    <td><strong>Wave Height:</strong></td>
                    <td>${currentSwh !== null ? currentSwh.toFixed(2) + ' m' : 'N/A'}</td>
                </tr>
                <tr>
                    <td><strong>Wave Period:</strong></td>
                    <td>${currentPeriod !== null ? currentPeriod.toFixed(1) + ' s' : 'N/A'}</td>
                </tr>
                <tr>
                    <td><strong>Wave Direction:</strong></td>
                    <td>${directionStr} (${currentDirection !== null ? currentDirection.toFixed(0) + '°' : 'N/A'})</td>
                </tr>
            </table>
        </div>
        <div style="padding: 10px; background: #f0f7ff; border-radius: 4px;">
            <div style="font-weight: bold; margin-bottom: 5px; color: #1e3c72;">10-Day Forecast Summary</div>
            <table style="width: 100%; font-size: 13px;">
                <tr>
                    <td><strong>Max Wave Height:</strong></td>
                    <td>${maxSwh.toFixed(2)} m</td>
                </tr>
                <tr>
                    <td><strong>Average Height:</strong></td>
                    <td>${avgSwh} m</td>
                </tr>
                <tr>
                    <td><strong>Forecast Hours:</strong></td>
                    <td>${timeseriesData.time.length}</td>
                </tr>
            </table>
        </div>
    `;

    // Create chart
    createForecastChart(timeseriesData.time, swh, perpw, dirpw);
}

// Convert direction degrees to compass direction
function getDirectionString(degrees) {
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    const index = Math.round(degrees / 22.5) % 16;
    return directions[index];
}

// Close forecast panel
function closeForecast() {
    document.getElementById('forecast-panel').classList.remove('active');
}

// Create forecast chart
let forecastChart = null;

function createForecastChart(times, swh, perpw, dirpw) {
    const ctx = document.getElementById('forecast-chart').getContext('2d');

    // Destroy existing chart
    if (forecastChart) {
        forecastChart.destroy();
    }

    // Parse times to Date objects
    const dateObjects = times.map(t => new Date(t));

    // Create readable labels - show date every 24 hours, otherwise just time
    const labels = dateObjects.map((d, i) => {
        const hours = d.getHours();
        if (hours === 0 || i === 0) {
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + '\n' +
                   d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        } else {
            return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }
    });

    const datasets = [{
        label: 'Significant Wave Height',
        data: swh,
        borderColor: '#1e3c72',
        backgroundColor: 'rgba(30, 60, 114, 0.1)',
        fill: true,
        yAxisID: 'y',
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4
    }];

    if (perpw && perpw.some(v => v !== null)) {
        datasets.push({
            label: 'Wave Period',
            data: perpw,
            borderColor: '#2a5298',
            backgroundColor: 'rgba(42, 82, 152, 0.1)',
            fill: false,
            yAxisID: 'y1',
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4
        });
    }

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            return dateObjects[index].toLocaleString();
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2);
                                label += context.datasetIndex === 0 ? ' m' : ' s';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 20
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Wave Height (m)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(30, 60, 114, 0.1)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: perpw && perpw.some(v => v !== null),
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Period (s)',
                        font: {
                            weight: 'bold'
                        }
                    },
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
    });
}

// Particle System Class
class ParticleSystem {
    constructor() {
        this.canvas = document.getElementById('particle-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.particleCount = 2000;
        this.speed = 0.5;
        this.enabled = true;
        this.animationId = null;
        this.data = null;
        this.variable = 'swh';
        this.maxAge = 50; // Particles live for 50 frames
    }

    init() {
        this.resize();
        this.createParticles();
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight - 60; // Account for header
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    setEnabled(enabled) {
        this.enabled = enabled;
        if (!enabled) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    setParticleCount(count) {
        this.particleCount = count;
        this.createParticles();
    }

    setSpeed(speed) {
        this.speed = speed;
    }

    updateData(data, variable) {
        this.data = data;
        this.variable = variable;
        // Clear canvas when data updates
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                age: Math.random() * this.maxAge,
                prevX: null,
                prevY: null
            });
        }
    }

    animate() {
        // Clear canvas completely to show map underneath
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.enabled && this.data) {
            this.particles.forEach(particle => {
                // Convert particle screen position to lat/lon
                const point = map.containerPointToLatLng([particle.x, particle.y - 60]);
                let lat = point.lat;
                let lon = point.lng;

                // Normalize longitude to data range (0-360)
                while (lon < 0) lon += 360;
                while (lon >= 360) lon -= 360;

                // Get wave data at this point
                const waveData = this.getWaveDataAtPoint(lat, lon);

                if (waveData && waveData.direction !== null && waveData.magnitude !== null) {
                    // Convert wave direction (meteorological: direction FROM) to radians
                    // dirpw is in degrees, 0 = from North, 90 = from East
                    // We want direction TO, so add 180 degrees
                    const directionTo = (waveData.direction + 180) % 360;
                    const angleRad = (directionTo - 90) * Math.PI / 180; // Convert to math angle (0 = East)

                    // Scale velocity by wave height and user speed setting
                    const velocity = (waveData.magnitude / 5) * this.speed * 2;

                    // Store previous position for trail
                    particle.prevX = particle.x;
                    particle.prevY = particle.y;

                    // Update position based on wave direction
                    particle.x += Math.cos(angleRad) * velocity;
                    particle.y += Math.sin(angleRad) * velocity;

                    // Age particle
                    particle.age += 1;

                    // Draw particle trail
                    if (particle.prevX !== null && particle.age < this.maxAge) {
                        const alpha = Math.max(0, 1 - particle.age / this.maxAge);

                        // Color based on wave height - blue for small, white for large
                        const intensity = Math.min(1, waveData.magnitude / 8);
                        const r = Math.floor(100 + 155 * intensity);
                        const g = Math.floor(150 + 105 * intensity);
                        const b = 255;

                        this.ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.8})`;
                        this.ctx.lineWidth = 2;
                        this.ctx.lineCap = 'round';
                        this.ctx.beginPath();
                        this.ctx.moveTo(particle.prevX, particle.prevY);
                        this.ctx.lineTo(particle.x, particle.y);
                        this.ctx.stroke();
                    }

                    // Reset particle if too old or out of bounds
                    if (particle.age > this.maxAge ||
                        particle.x < 0 || particle.x > this.canvas.width ||
                        particle.y < 0 || particle.y > this.canvas.height) {
                        particle.x = Math.random() * this.canvas.width;
                        particle.y = Math.random() * this.canvas.height;
                        particle.age = 0;
                        particle.prevX = null;
                        particle.prevY = null;
                    }
                } else {
                    // No data at this location, reset particle
                    particle.x = Math.random() * this.canvas.width;
                    particle.y = Math.random() * this.canvas.height;
                    particle.age = 0;
                    particle.prevX = null;
                    particle.prevY = null;
                }
            });
        }

        this.animationId = requestAnimationFrame(() => this.animate());
    }

    getWaveDataAtPoint(lat, lon) {
        if (!this.data || !this.data.variables.swh || !this.data.variables.dirpw) {
            return null;
        }

        // Bilinear interpolation for smooth visualization
        const latIdx = this.findGridIndex(this.data.latitude, lat);
        const lonIdx = this.findGridIndex(this.data.longitude, lon);

        if (latIdx === -1 || lonIdx === -1) return null;

        // Get neighboring grid points for interpolation
        const latIdx0 = latIdx;
        const latIdx1 = Math.min(latIdx + 1, this.data.latitude.length - 1);
        const lonIdx0 = lonIdx;
        const lonIdx1 = Math.min(lonIdx + 1, this.data.longitude.length - 1);

        // Simple nearest-neighbor (can be upgraded to bilinear interpolation)
        const magnitude = this.data.variables.swh[latIdx0][lonIdx0];
        const direction = this.data.variables.dirpw[latIdx0][lonIdx0];

        if (magnitude === null || direction === null) return null;

        return { magnitude, direction };
    }

    findGridIndex(array, value) {
        // Binary search for efficiency
        let minDist = Infinity;
        let minIdx = -1;

        for (let i = 0; i < array.length; i++) {
            const dist = Math.abs(array[i] - value);
            if (dist < minDist) {
                minDist = dist;
                minIdx = i;
            }
        }

        return minIdx;
    }
}

// Start the application when page loads
window.addEventListener('load', init);
