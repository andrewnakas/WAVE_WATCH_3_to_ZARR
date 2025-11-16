#!/usr/bin/env python3
"""
Extract web-friendly data from WW3 Zarr for GitHub Pages visualization.
Creates JSON files with:
- Latest timestep data (sampled for performance)
- Time series data for 16-day forecasts at grid points
"""

import sys
import json
from pathlib import Path
import xarray as xr
import numpy as np

def extract_web_data(zarr_path, output_dir):
    """Extract Zarr data to web-friendly JSON format."""

    print(f"Opening Zarr dataset: {zarr_path}")
    ds = xr.open_zarr(zarr_path)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Extract metadata
    print("\n1. Extracting metadata...")
    metadata = {
        'variables': list(ds.data_vars),
        'dimensions': dict(ds.sizes),
        'bounds': {
            'lat_min': float(ds.latitude.min()),
            'lat_max': float(ds.latitude.max()),
            'lon_min': float(ds.longitude.min()),
            'lon_max': float(ds.longitude.max())
        },
        'time_range': {
            'start': str(ds.time.values[0]) if 'time' in ds.sizes else str(ds.time.values),
            'end': str(ds.time.values[-1]) if 'time' in ds.sizes and len(ds.time) > 1 else str(ds.time.values),
            'count': int(ds.sizes.get('time', 1))
        },
        'attributes': {k: str(v) for k, v in ds.attrs.items()}
    }

    with open(output_path / 'metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  ✓ Saved metadata.json")

    # 2. Extract latest timestep data (sampled for web performance)
    print("\n2. Extracting latest timestep data...")

    # Sample every Nth point to reduce data size for web
    # For 0.16° resolution (406x2160), sampling every 4 points gives ~101x540 grid
    sample_lat = 4
    sample_lon = 4

    if 'time' in ds.sizes and len(ds.time) > 0:
        latest_ds = ds.isel(time=-1)  # Last timestep
        time_idx = -1
    else:
        latest_ds = ds
        time_idx = 0

    # Sample the grid
    sampled_ds = latest_ds.isel(
        latitude=slice(None, None, sample_lat),
        longitude=slice(None, None, sample_lon)
    )

    # Extract key variables for visualization
    latest_data = {
        'latitude': sampled_ds.latitude.values.tolist(),
        'longitude': sampled_ds.longitude.values.tolist(),
        'time': str(ds.time.values[time_idx]) if 'time' in ds.sizes else str(ds.time.values),
        'variables': {}
    }

    # Convert wave variables to lists
    for var in ['swh', 'perpw', 'dirpw', 'shww', 'mpww', 'wvdir', 'shts', 'mpts', 'swdir']:
        if var in sampled_ds:
            # Get values and ensure it's 2D (lat, lon)
            values = sampled_ds[var].values

            # Squeeze out any singleton dimensions
            values = np.squeeze(values)

            # Ensure we have a 2D array
            if values.ndim != 2:
                print(f"  ⚠ Warning: {var} has {values.ndim} dimensions, expected 2. Skipping.")
                continue

            # Replace NaN with None for JSON using vectorized operations
            # Convert to object array to allow None values
            values_obj = values.astype(object)
            values_obj[np.isnan(values)] = None

            # Convert to nested list
            values_list = values_obj.tolist()

            latest_data['variables'][var] = values_list
            print(f"  ✓ Extracted {var}: {len(latest_data['latitude'])}x{len(latest_data['longitude'])} grid")

    with open(output_path / 'latest_data.json', 'w') as f:
        json.dump(latest_data, f)
    print(f"  ✓ Saved latest_data.json ({len(latest_data['latitude'])}x{len(latest_data['longitude'])} grid)")

    # 3. Extract time series data for 5-day forecasts
    print("\n3. Extracting time series for 5-day forecasts...")

    if 'time' not in ds.sizes or len(ds.time) <= 1:
        print("  ⓘ Skipping time series (single timestep dataset)")
        time_series = {
            'note': 'Single timestep dataset - no time series available',
            'grid_spacing': {'lat': sample_lat * 0.16, 'lon': sample_lon * 0.16}
        }
    else:
        # Sample time series data (every 4th point in each dimension)
        sampled_ts = ds.isel(
            latitude=slice(None, None, sample_lat),
            longitude=slice(None, None, sample_lon)
        )

        # Extract time values
        time_values = [str(t) for t in sampled_ts.time.values]

        # For each variable, create a 3D array [lat][lon][time]
        time_series = {
            'latitude': sampled_ts.latitude.values.tolist(),
            'longitude': sampled_ts.longitude.values.tolist(),
            'time': time_values,
            'grid_spacing': {
                'lat': sample_lat * 0.16,
                'lon': sample_lon * 0.16
            },
            'variables': {}
        }

        # Extract significant wave height time series (most important)
        for var in ['swh', 'perpw', 'dirpw']:
            if var in sampled_ts:
                print(f"  → Processing {var}...")
                values = sampled_ts[var].values

                # Expected shape: [time, lat, lon]
                # We want output: [lat][lon][time]
                # Transpose to [lat, lon, time]
                values_transposed = np.transpose(values, (1, 2, 0))

                # Convert to object array to allow None values
                values_obj = values_transposed.astype(object)

                # Create mask for NaN values
                nan_mask = np.isnan(values_transposed)
                values_obj[nan_mask] = None

                # Convert to nested list [lat][lon][time]
                var_data = values_obj.tolist()

                time_series['variables'][var] = var_data
                print(f"  ✓ Extracted {var} time series")

        with open(output_path / 'timeseries_data.json', 'w') as f:
            json.dump(time_series, f)
        print(f"  ✓ Saved timeseries_data.json ({len(time_series['latitude'])}x{len(time_series['longitude'])}x{len(time_series['time'])} grid)")

    # 4. Create a lightweight summary for quick loading
    print("\n4. Creating lightweight summary...")
    summary = {
        'run_time': metadata['time_range']['start'],
        'forecast_length_hours': int(ds.sizes.get('time', 1)) if 'time' in ds.sizes else 0,
        'grid_size': {
            'full': {'lat': ds.sizes['latitude'], 'lon': ds.sizes['longitude']},
            'sampled': {'lat': len(latest_data['latitude']), 'lon': len(latest_data['longitude'])}
        },
        'sample_rate': {'lat': sample_lat, 'lon': sample_lon},
        'data_files': {
            'metadata': 'metadata.json',
            'latest': 'latest_data.json',
            'timeseries': 'timeseries_data.json' if 'time' in ds.sizes and len(ds.time) > 1 else None
        }
    }

    with open(output_path / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Saved summary.json")

    # 5. Print summary
    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print("="*70)
    print(f"Output directory: {output_path}")
    print(f"Files created:")
    for file in output_path.glob('*.json'):
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  - {file.name}: {size_mb:.2f} MB")

    ds.close()
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_web_data.py <zarr_path> [output_dir]")
        print("\nExample:")
        print("  python extract_web_data.py data/zarr/latest.zarr docs/data")
        sys.exit(1)

    zarr_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'docs/data'

    if not Path(zarr_path).exists():
        print(f"Error: Zarr dataset not found at {zarr_path}")
        sys.exit(1)

    success = extract_web_data(zarr_path, output_dir)
    sys.exit(0 if success else 1)
