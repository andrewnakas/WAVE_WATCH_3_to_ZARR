# WAVE WATCH 3 to Zarr Data Pipeline

Automated pipeline that downloads the latest WAVE WATCH III (WW3) global wave model data from NOAA and converts it to Zarr format for efficient access and analysis.

## Overview

This repository contains a GitHub Actions workflow that:

1. **Downloads** the latest WW3 global wave forecast data from NOAA NOMADS
2. **Converts** GRIB2 format to Zarr for cloud-optimized storage
3. **Stores** the converted data in this repository for easy access
4. **Visualizes** the data on an interactive map with wave particle animations
5. **Runs automatically** every 6 hours, synchronized with NOAA's model run schedule

## 🌊 Interactive Visualization

**[View Live Visualization →](https://andrewnakas.github.io/WAVE_WATCH_3_to_ZARR/)**

The repository includes an interactive GitHub Pages visualization featuring:

- **Global Wave Map**: Leaflet-based map showing real-time wave conditions
- **Wave Particle Animation**: Dynamic visualization of wave movement patterns using actual wave direction data
- **10-Day Forecast**: Click any point on the map to see the complete forecast time series
- **Multiple Variables**: Toggle between wave height, period, direction, wind waves, and swell

The visualization automatically updates every 6 hours with the latest forecast data.

## Data Source

- **Provider:** NOAA National Centers for Environmental Prediction (NCEP)
- **Model:** WAVE WATCH III (WW3) Global Wave Model
- **Resolution:** 0.16° (~16 km) global grid
- **Update Frequency:** Every 6 hours (00, 06, 12, 18 UTC)
- **Source URL:** https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/

## WW3 Model Variables

This dataset contains **9 wave-specific variables** from WAVE WATCH III. Wind variables (u, v, ws, wdir) are excluded since they're already available in standard GFS forecasts.

### Combined Wave Parameters
- **swh** - Significant height of combined wind waves and swell (m)
- **perpw** - Primary wave mean period (s)
- **dirpw** - Primary wave direction (degrees)

### Wind Wave Parameters
- **shww** - Significant height of wind waves (m)
- **mpww** - Mean period of wind waves (s)
- **wvdir** - Direction of wind waves (degrees)

### Swell Parameters (1st partition)
- **shts** - Significant height of swell waves (m)
- **mpts** - Mean period of swell waves (s)
- **swdir** - Direction of swell waves (degrees)

**Note:** 2nd and 3rd swell partitions are not currently extracted due to cfgrib limitations in reading all GRIB message groups. Wind data (u, v, ws, wdir) is excluded to reduce storage and avoid duplicating data already in standard GFS.

### Forecast Hours

WW3 provides forecasts with the following schedule:
- **f000-f120**: Hourly forecasts (0, 1, 2, ..., 120 hours)
- **f120-f384**: 3-hourly forecasts (120, 123, 126, ..., 384 hours)

By default, only **f000** (analysis/nowcast) is downloaded. You can configure multiple forecast hours using the `--forecast-hours` option.

## Repository Structure

```
WAVE_WATCH_3_to_ZARR/
├── .github/
│   └── workflows/
│       └── ww3_download.yml    # Scheduled GitHub Action
├── data/
│   └── zarr/                   # Zarr datasets (git-tracked)
│       ├── ww3_global_YYYYMMDD_HH.zarr/
│       └── latest.zarr         # Symlink to latest run
├── download_ww3.py             # Main download & conversion script
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## GitHub Actions Workflow

### Schedule

The workflow runs on a schedule:
- **Cron:** `30 0,6,12,18 * * *` (30 minutes after each WW3 model run)
- **Manual:** Can be triggered manually via GitHub Actions UI

### Workflow Steps

1. Checkout repository
2. Set up Python 3.11
3. Install system dependencies (eccodes for GRIB2 support)
4. Install Python packages (xarray, cfgrib, zarr, etc.)
5. Download latest WW3 GRIB2 data (10-day hourly forecast, 241 timesteps)
6. Convert to Zarr format using incremental writing
7. Upload Zarr dataset as GitHub Actions artifact

### Accessing the Data

**Zarr datasets are stored as GitHub Actions artifacts** (not committed to git due to size):

1. Go to the [Actions tab](../../actions)
2. Click on the most recent "Download and Convert WW3 Data" workflow run
3. Download the `ww3-zarr-latest` artifact (bottom of the page)
4. Extract and use locally

**Retention:** Artifacts are kept for 14 days

**Why artifacts?** The 10-day Zarr dataset (~2.0-3.0 GB) exceeds GitHub's recommended push size limits. Storing in artifacts avoids repository bloat while making data easily downloadable.

## Local Usage

### Prerequisites

**System Dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install libeccodes-dev libeccodes-tools

# macOS
brew install eccodes

# Conda (cross-platform)
conda install -c conda-forge eccodes
```

**Python Dependencies:**
```bash
pip install -r requirements.txt
```

### Running Locally

**Basic Usage (single forecast hour):**
```bash
# Download and convert latest WW3 analysis (f000)
python download_ww3.py
```

**Download Multiple Forecast Hours:**
```bash
# Download first 24 hours at 3-hour intervals (f000, f003, f006, ..., f024)
python download_ww3.py --forecast-hours "0-24:3"

# Download specific hours (f000, f006, f012, f024)
python download_ww3.py --forecast-hours "0,6,12,24"

# Download first 5 days at 6-hour intervals
python download_ww3.py --forecast-hours "0-120:6"
```

**Using Environment Variable:**
```bash
# Set forecast hours via environment variable
export WW3_FORECAST_HOURS="0-48:3"
python download_ww3.py
```

The script will:
1. Determine the latest available model run
2. Download GRIB2 data from NOAA NOMADS
3. Convert to Zarr format with 9 wave-specific variables (excludes wind)
4. Save to `data/zarr/ww3_global_YYYYMMDD_HH.zarr/` or `ww3_global_YYYYMMDD_HH_fXXX-fXXX.zarr`
5. Create a `latest.zarr` symlink

### Reading Zarr Data

```python
import xarray as xr

# Open the latest dataset
ds = xr.open_zarr('data/zarr/latest.zarr')

# View dataset info
print(ds)
print(f"Variables: {list(ds.data_vars)}")
print(f"Dimensions: {dict(ds.dims)}")

# Access variables
wave_height = ds['swh']     # Significant wave height (combined waves + swell)
wave_period = ds['perpw']   # Primary wave mean period
wave_direction = ds['dirpw'] # Primary wave direction
wind_speed = ds['ws']       # Wind speed at 10m
swell_1_height = ds['shts'] # First swell partition height

# Example: Plot global wave heights
import matplotlib.pyplot as plt

# If multiple time steps, select first
if 'time' in wave_height.dims:
    wave_height.isel(time=0).plot(figsize=(12, 6))
else:
    wave_height.plot(figsize=(12, 6))

plt.title('Global Significant Wave Height (m)')
plt.show()

# Example: Compare wind waves vs swell
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

ds['shww'].plot(ax=ax1)  # Wind waves
ax1.set_title('Wind Wave Height (m)')

ds['shts'].plot(ax=ax2)  # Swell (1st partition)
ax2.set_title('Swell Height (m) - 1st Partition')

plt.tight_layout()
plt.show()
```

## Data Format

### Zarr Structure

The Zarr datasets are stored in a hierarchical directory structure:

```
ww3_global_20251116_00.zarr/
├── .zarray           # Array metadata
├── .zattrs           # Dataset attributes
├── .zgroup           # Group metadata
├── latitude/         # Coordinate arrays
├── longitude/
├── time/
└── [variables]/      # Data variables (HTSGW, PERPW, etc.)
```

### Advantages of Zarr

- **Cloud-optimized:** Efficient chunk-based access
- **Compression:** Smaller storage footprint
- **Parallel I/O:** Fast multi-threaded reads
- **No decompression:** Direct array access
- **Compatible:** Works with xarray, dask, and many tools

## Data Retention

- **GitHub Actions artifacts:** 14 days retention
- **GRIB2 files:** Automatically cleaned up after conversion to save space
- **Local data:** Managed by user (no automatic cleanup)

## Monitoring

GitHub Actions provides:
- **Workflow run logs:** Detailed execution logs for each run
- **Summary reports:** Overview of downloaded data and sizes
- **Email notifications:** On workflow failures (configurable)

## Contributing

To modify the pipeline:

1. Edit `download_ww3.py` for data processing changes
2. Edit `.github/workflows/ww3_download.yml` for workflow changes
3. Test locally before committing
4. Push to the `claude/wave-watch-data-pipeline-*` branch

## Resources

- [WAVE WATCH III Documentation](https://polar.ncep.noaa.gov/waves/wavewatch/)
- [NOAA NOMADS Data Access](https://nomads.ncep.noaa.gov/)
- [Zarr Documentation](https://zarr.readthedocs.io/)
- [xarray Documentation](https://docs.xarray.dev/)
- [cfgrib Documentation](https://github.com/ecmwf/cfgrib)

## License

This repository is for educational and research purposes. NOAA wave model data is publicly available.

## Support

For issues or questions:
- Check GitHub Actions logs for workflow failures
- Review NOAA NOMADS status for data availability issues
- Open an issue in this repository for bugs or feature requests

---

**Last Updated:** 2025-11-16
**Maintained by:** Automated GitHub Actions Workflow
