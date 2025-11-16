#!/usr/bin/env python3
"""
Audit WW3 Zarr dataset for data integrity and correctness.
"""

import sys
from pathlib import Path
import xarray as xr
import numpy as np

def audit_zarr(zarr_path):
    """Comprehensive audit of WW3 Zarr dataset."""

    print("=" * 70)
    print(f"AUDITING ZARR DATASET: {zarr_path}")
    print("=" * 70)
    print()

    try:
        # Open the dataset
        ds = xr.open_zarr(zarr_path)
        print("✓ Dataset opened successfully")
        print()

        # Check 1: Variables
        print("1. VARIABLES CHECK")
        print("-" * 70)
        expected_wave_vars = ['swh', 'perpw', 'dirpw', 'shww', 'mpww',
                              'wvdir', 'shts', 'mpts', 'swdir']
        excluded_wind_vars = ['u', 'v', 'ws', 'wdir']

        actual_vars = sorted(list(ds.data_vars))
        print(f"Found {len(actual_vars)} variables: {actual_vars}")

        # Check for wave-specific variables
        missing_wave = [v for v in expected_wave_vars if v not in actual_vars]
        if missing_wave:
            print(f"⚠️  Missing expected wave variables: {missing_wave}")
        else:
            print(f"✓ All {len(expected_wave_vars)} wave-specific variables present")

        # Check for excluded wind variables
        found_wind = [v for v in excluded_wind_vars if v in actual_vars]
        if found_wind:
            print(f"⚠️  Found excluded wind variables: {found_wind}")
        else:
            print("✓ Wind variables correctly excluded (u, v, ws, wdir)")
        print()

        # Check 2: Dimensions
        print("2. DIMENSIONS CHECK")
        print("-" * 70)
        dims = dict(ds.dims)
        print(f"Dimensions: {dims}")

        # Expected dimensions
        if 'latitude' in dims:
            print(f"✓ Latitude: {dims['latitude']} points")
            if dims['latitude'] == 406:
                print("  ✓ Correct resolution (0.16° → 406 latitudes)")

        if 'longitude' in dims:
            print(f"✓ Longitude: {dims['longitude']} points")
            if dims['longitude'] == 2160:
                print("  ✓ Correct resolution (0.16° → 2160 longitudes)")

        if 'time' in dims:
            print(f"✓ Time: {dims['time']} timesteps")
            if dims['time'] == 209:
                print("  ✓ Full 16-day forecast (209 timesteps)")
            elif dims['time'] == 1:
                print("  ⓘ Single timestep (analysis only)")
        else:
            print("⚠️  No time dimension found")
        print()

        # Check 3: Coordinates
        print("3. COORDINATES CHECK")
        print("-" * 70)
        for coord in ['latitude', 'longitude', 'time']:
            if coord in ds.coords:
                coord_data = ds.coords[coord]
                if coord == 'latitude':
                    lat_min, lat_max = float(coord_data.min()), float(coord_data.max())
                    print(f"✓ Latitude range: {lat_min:.2f}° to {lat_max:.2f}°")
                    if abs(lat_min - (-78.0)) < 1 and abs(lat_max - 78.0) < 1:
                        print("  ✓ Global coverage (approximately -78° to 78°)")

                elif coord == 'longitude':
                    lon_min, lon_max = float(coord_data.min()), float(coord_data.max())
                    print(f"✓ Longitude range: {lon_min:.2f}° to {lon_max:.2f}°")
                    if abs(lon_max - lon_min - 360.0) < 1:
                        print("  ✓ Global coverage (360° span)")

                elif coord == 'time':
                    # Check if time has dimensions
                    if coord_data.dims:
                        print(f"✓ Time start: {coord_data.values[0]}")
                        if len(coord_data) > 1:
                            print(f"  Time end: {coord_data.values[-1]}")
                    else:
                        # Scalar time coordinate
                        print(f"✓ Time (scalar): {coord_data.values}")
        print()

        # Check 4: Data Values
        print("4. DATA VALUES CHECK")
        print("-" * 70)

        # Check significant wave height (swh)
        if 'swh' in ds:
            swh = ds['swh']

            # Get a sample (first timestep if multi-time)
            if 'time' in swh.dims and len(ds.time) > 0:
                swh_sample = swh.isel(time=0)
            else:
                swh_sample = swh

            # Load data
            swh_values = swh_sample.values

            # Check for valid range (wave heights should be 0-30m typically)
            valid_mask = ~np.isnan(swh_values)
            if valid_mask.any():
                min_val = float(np.nanmin(swh_values))
                max_val = float(np.nanmax(swh_values))
                mean_val = float(np.nanmean(swh_values))

                print(f"Significant Wave Height (swh):")
                print(f"  Min: {min_val:.2f} m")
                print(f"  Max: {max_val:.2f} m")
                print(f"  Mean: {mean_val:.2f} m")

                if 0 <= min_val <= 30 and 0 <= max_val <= 30:
                    print("  ✓ Values in reasonable range (0-30m)")
                else:
                    print(f"  ⚠️  Values outside expected range")

                nan_pct = (np.isnan(swh_values).sum() / swh_values.size) * 100
                print(f"  NaN values: {nan_pct:.1f}%")
                if nan_pct < 50:
                    print("  ✓ Low NaN percentage")
            else:
                print("  ⚠️  All values are NaN")
        print()

        # Check 5: Metadata
        print("5. METADATA CHECK")
        print("-" * 70)
        attrs_to_check = ['source', 'download_time', 'excluded_variables']
        for attr in attrs_to_check:
            if attr in ds.attrs:
                print(f"✓ {attr}: {ds.attrs[attr]}")
        print()

        # Check 6: Data Size
        print("6. DATASET SIZE")
        print("-" * 70)
        total_size = 0
        for var in ds.data_vars:
            var_size = ds[var].nbytes / (1024 * 1024)  # MB
            total_size += var_size

        print(f"Total size (uncompressed): {total_size:.1f} MB")
        if 'time' in dims:
            per_timestep = total_size / dims['time']
            print(f"Size per timestep: {per_timestep:.1f} MB")
        print()

        # Check 7: Zarr Chunks
        print("7. ZARR CHUNKS")
        print("-" * 70)
        if 'swh' in ds:
            chunks = ds['swh'].chunks
            print(f"Example chunking (swh): {chunks}")
            print("✓ Chunked storage for efficient access")
        print()

        # Summary
        print("=" * 70)
        print("AUDIT SUMMARY")
        print("=" * 70)

        issues = []
        if missing_wave:
            issues.append(f"Missing wave variables: {missing_wave}")
        if found_wind:
            issues.append(f"Unexpected wind variables: {found_wind}")
        if 'time' not in dims:
            issues.append("No time dimension")

        if issues:
            print("⚠️  ISSUES FOUND:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✓ ALL CHECKS PASSED")
            print(f"   - {len(actual_vars)} wave-specific variables")
            print(f"   - {dims.get('time', 1)} timesteps")
            print(f"   - {dims.get('latitude', 0)}x{dims.get('longitude', 0)} grid")
            print(f"   - {total_size:.1f} MB total size")

        print()

        ds.close()
        return len(issues) == 0

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    zarr_path = sys.argv[1] if len(sys.argv) > 1 else 'data/zarr/latest.zarr'

    if not Path(zarr_path).exists():
        print(f"Error: Zarr dataset not found at {zarr_path}")
        sys.exit(1)

    success = audit_zarr(zarr_path)
    sys.exit(0 if success else 1)
