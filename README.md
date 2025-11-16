# WAVE WATCH 3 to Zarr Data Pipeline

Automated pipeline that downloads the latest WAVE WATCH III (WW3) global wave model data from NOAA and converts it to Zarr format for efficient access and analysis.

## Overview

This repository contains a GitHub Actions workflow that:

1. **Downloads** the latest WW3 global wave forecast data from NOAA NOMADS
2. **Converts** GRIB2 format to Zarr for cloud-optimized storage
3. **Stores** the converted data in this repository for easy access
4. **Runs automatically** every 6 hours, synchronized with NOAA's model run schedule

## Data Source

- **Provider:** NOAA National Centers for Environmental Prediction (NCEP)
- **Model:** WAVE WATCH III (WW3) Global Wave Model
- **Resolution:** 0.16° (~16 km) global grid
- **Update Frequency:** Every 6 hours (00, 06, 12, 18 UTC)
- **Source URL:** https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/

## WW3 Model Variables

The WAVE WATCH III model typically includes the following wave parameters:

- **HTSGW** - Significant height of combined wind waves and swell (m)
- **PERPW** - Primary wave mean period (s)
- **DIRPW** - Primary wave direction (degrees)
- **WVHGT** - Significant height of wind waves (m)
- **WVPER** - Mean period of wind waves (s)
- **WVDIR** - Direction of wind waves (degrees)
- **SWELL** - Significant height of swell waves (m)
- **SWPER** - Mean period of swell waves (s)
- **SWDIR** - Direction of swell waves (degrees)
- **WIND** - Wind speed at 10m (m/s)
- **WDIR** - Wind direction (degrees)

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
5. Download latest WW3 GRIB2 data
6. Convert to Zarr format
7. Commit and push Zarr data to repository

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

```bash
# Download and convert latest WW3 data
python download_ww3.py
```

The script will:
1. Determine the latest available model run
2. Download GRIB2 data from NOAA NOMADS
3. Convert to Zarr format
4. Save to `data/zarr/ww3_global_YYYYMMDD_HH.zarr/`
5. Create a `latest.zarr` symlink

### Reading Zarr Data

```python
import xarray as xr

# Open the latest dataset
ds = xr.open_zarr('data/zarr/latest.zarr')

# View dataset info
print(ds)

# Access variables
wave_height = ds['HTSGW']  # Significant wave height
wave_period = ds['PERPW']   # Primary wave period
wave_direction = ds['DIRPW'] # Primary wave direction

# Example: Plot global wave heights
import matplotlib.pyplot as plt

wave_height.isel(time=0).plot(figsize=(12, 6))
plt.title('Global Significant Wave Height')
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

- The repository keeps Zarr datasets from recent runs
- Old GRIB2 files are automatically cleaned up after conversion
- Consider implementing data retention policies based on storage limits

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
