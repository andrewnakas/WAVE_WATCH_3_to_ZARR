# WW3 Zarr Data Verification Guide

## How to Verify the Zarr Dataset

### 1. Download the Latest Artifact

1. Go to [GitHub Actions](../../actions)
2. Click on the latest **"Download and Convert WW3 Data"** workflow run
3. Download the **`ww3-zarr-latest`** artifact
4. Extract the `.zarr` directory

### 2. Run the Audit Script

```bash
python audit_zarr.py path/to/ww3_global_YYYYMMDD_HH_f000-f384.zarr
```

### 3. Expected Results

A **valid full 16-day forecast** should show:

#### ✓ Variables (9 wave-specific)
```
✓ All 9 wave-specific variables present
✓ Wind variables correctly excluded (u, v, ws, wdir)

Variables: ['dirpw', 'mpts', 'mpww', 'perpw', 'shts',
            'shww', 'swdir', 'swh', 'wvdir']
```

#### ✓ Dimensions
```
✓ Latitude: 406 points (0.16° resolution)
✓ Longitude: 2160 points (0.16° resolution)
✓ Time: 209 timesteps (full 16-day forecast)
```

#### ✓ Coordinates
```
✓ Latitude range: approximately -78° to 78°
✓ Longitude range: 0° to 360° (global coverage)
✓ Time start: 2025-11-16T00:00:00
  Time end: 2025-12-02T00:00:00 (16 days later)
```

#### ✓ Data Values (example: swh)
```
Min: ~0.00 m
Max: ~25.00 m (varies by conditions)
Mean: ~1.50-3.00 m (varies)
✓ Values in reasonable range (0-30m)
✓ Low NaN percentage (<50%)
```

#### ✓ Size
```
Total size: ~2.5-3.0 GB (uncompressed)
Size per timestep: ~12-14 MB
```

## Common Issues

### Issue: Wind variables found
**Symptom:** `⚠️  Found excluded wind variables: ['u', 'v', 'ws', 'wdir']`
**Cause:** Old dataset from before wind filtering was added
**Fix:** Download latest artifact from recent workflow run

### Issue: Only 1 timestep
**Symptom:** `⚠️  No time dimension` or `Time: 1 timesteps`
**Cause:** Workflow ran with default settings (f000 only)
**Fix:** Check that `WW3_FORECAST_HOURS="0-120,123-384:3"` is set in workflow

### Issue: Missing variables
**Symptom:** `⚠️  Missing expected wave variables: [...]`
**Cause:** GRIB download or conversion failure
**Fix:** Check workflow logs for errors, retry workflow

## Manual Data Validation

### Python Example

```python
import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_zarr('path/to/dataset.zarr')

# 1. Check structure
print(f"Variables: {list(ds.data_vars)}")
print(f"Dimensions: {dict(ds.dims)}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")

# 2. Validate wave heights
swh = ds['swh']
print(f"\\nSignificant Wave Height stats:")
print(f"  Min: {float(swh.min()):.2f} m")
print(f"  Max: {float(swh.max()):.2f} m")
print(f"  Mean: {float(swh.mean()):.2f} m")

# 3. Check temporal consistency
if len(ds.time) > 1:
    # Check time intervals
    time_diff = np.diff(ds.time.values)
    print(f"\\nTime intervals: {time_diff[:5]}")  # First 5

# 4. Spatial coverage check
print(f"\\nLatitude: {float(ds.latitude.min()):.1f}° to {float(ds.latitude.max()):.1f}°")
print(f"Longitude: {float(ds.longitude.min()):.1f}° to {float(ds.longitude.max()):.1f}°")

# 5. Sample data at specific location
# Example: Check wave height near Hawaii (20°N, 200°E)
hawaii_swh = ds['swh'].sel(latitude=20, longitude=200, method='nearest')
print(f"\\nWave height near Hawaii (20°N, 200°E):")
print(f"  Time series: {hawaii_swh.values}")

ds.close()
```

## Data Quality Checklist

- [ ] 9 wave-specific variables present
- [ ] No wind variables (u, v, ws, wdir)
- [ ] 209 timesteps (full 16-day forecast)
- [ ] 406 × 2160 spatial grid (0.16° resolution)
- [ ] Global coverage (-78° to 78° lat, 0° to 360° lon)
- [ ] Wave heights in reasonable range (0-30m)
- [ ] Low NaN percentage (<50%)
- [ ] Temporal consistency (hourly to f120, 3-hourly beyond)
- [ ] ~2.5 GB total size
- [ ] Dataset can be opened and read with xarray

## Contact

If audit shows persistent issues, check:
1. GitHub Actions workflow logs
2. NOAA NOMADS data availability
3. cfgrib version compatibility

---

**Last Updated:** 2025-11-16
**Dataset Version:** Full 16-day forecast with wave-only variables
