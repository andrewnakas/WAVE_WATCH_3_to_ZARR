# WAVE WATCH 3 Interactive Visualization

This directory contains the GitHub Pages site for visualizing WAVE WATCH 3 global wave forecast data.

## Features

- **Interactive Leaflet Map**: Global view of wave conditions
- **Wave Particle Animation**: Real-time visualization of wave movement patterns
- **5-Day Forecast**: Click any point on the map to see the full forecast time series
- **Multiple Variables**: Toggle between different wave parameters:
  - Significant Wave Height (swh)
  - Wave Period (perpw)
  - Wave Direction (dirpw)
  - Wind Wave Height (shww)
  - Swell Height (shts)

## How It Works

The GitHub Actions workflow automatically:

1. Downloads the latest WW3 GRIB2 data from NOAA
2. Converts to Zarr format
3. Extracts web-friendly JSON data (sampled grid for performance)
4. Deploys to GitHub Pages

## Data Files

The `data/` directory contains JSON files generated from the Zarr dataset:

- `summary.json` - Metadata about the dataset
- `metadata.json` - Full dataset metadata
- `latest_data.json` - Latest timestep data (sampled every 4th grid point)
- `timeseries_data.json` - Time series data for 5-day forecasts

## Technologies Used

- **Leaflet.js** - Interactive mapping
- **Chart.js** - Forecast time series charts
- **Canvas API** - Wave particle animation
- **Vanilla JavaScript** - No framework dependencies

## Accessing the Visualization

Once deployed, the visualization is available at:

```
https://<username>.github.io/WAVE_WATCH_3_to_ZARR/
```

## Local Development

To test locally:

1. Extract web data from a Zarr dataset:
   ```bash
   python extract_web_data.py data/zarr/latest.zarr docs/data
   ```

2. Serve the `docs/` directory with a local web server:
   ```bash
   cd docs
   python -m http.server 8000
   ```

3. Open http://localhost:8000 in your browser

## Performance Notes

- The grid is sampled every 4th point (from 406×2160 to ~101×540) to reduce data size
- Only key variables (swh, perpw, dirpw) are included in time series data
- Particle count and speed are adjustable via controls
- Total web data size: ~5-20 MB (compared to ~2.5 GB full Zarr)

## Credits

- **Data Source**: NOAA NCEP WAVE WATCH III Global Model
- **Map Tiles**: OpenStreetMap contributors
- **Libraries**: Leaflet.js, Chart.js
