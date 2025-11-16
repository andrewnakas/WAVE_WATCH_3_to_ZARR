#!/usr/bin/env python3
"""
Example script showing how to read and work with WW3 Zarr data.
"""

import xarray as xr
from pathlib import Path
import sys


def main():
    """Demonstrate reading and exploring WW3 Zarr data."""

    # Path to latest Zarr dataset
    zarr_path = Path('data/zarr/latest.zarr')

    if not zarr_path.exists():
        print("❌ No Zarr data found. Please run download_ww3.py first.")
        print(f"   Looking for: {zarr_path.absolute()}")
        sys.exit(1)

    print(f"📂 Opening Zarr dataset: {zarr_path}")
    print()

    # Open the dataset
    ds = xr.open_zarr(zarr_path)

    # Display basic information
    print("=" * 60)
    print("WAVE WATCH III Dataset Information")
    print("=" * 60)
    print()

    # Metadata
    if 'source' in ds.attrs:
        print(f"Source: {ds.attrs['source']}")
    if 'download_time' in ds.attrs:
        print(f"Downloaded: {ds.attrs['download_time']}")
    if 'original_file' in ds.attrs:
        print(f"Original file: {ds.attrs['original_file']}")
    print()

    # Dimensions
    print("Dimensions:")
    for dim, size in ds.dims.items():
        print(f"  {dim}: {size}")
    print()

    # Coordinates
    print("Coordinates:")
    for coord in ds.coords:
        coord_data = ds.coords[coord]
        print(f"  {coord}: {coord_data.dims} - {coord_data.dtype}")
    print()

    # Data variables
    print("Data Variables:")
    for var in ds.data_vars:
        var_data = ds[var]
        shape = var_data.shape
        dtype = var_data.dtype

        # Get variable attributes if available
        long_name = var_data.attrs.get('long_name', 'N/A')
        units = var_data.attrs.get('units', 'N/A')

        print(f"  {var}:")
        print(f"    Shape: {shape}")
        print(f"    Type: {dtype}")
        print(f"    Description: {long_name}")
        print(f"    Units: {units}")
        print()

    # Example: Get statistics for first variable
    if len(ds.data_vars) > 0:
        first_var = list(ds.data_vars)[0]
        print(f"Statistics for {first_var}:")

        data = ds[first_var]

        # If time dimension exists, select first timestep
        if 'time' in data.dims:
            data = data.isel(time=0)

        print(f"  Min: {float(data.min().values):.4f}")
        print(f"  Max: {float(data.max().values):.4f}")
        print(f"  Mean: {float(data.mean().values):.4f}")
        print(f"  Std: {float(data.std().values):.4f}")
        print()

    # Spatial extent
    if 'latitude' in ds.coords and 'longitude' in ds.coords:
        lat = ds.coords['latitude']
        lon = ds.coords['longitude']
        print("Spatial Extent:")
        print(f"  Latitude: {float(lat.min().values):.2f}° to {float(lat.max().values):.2f}°")
        print(f"  Longitude: {float(lon.min().values):.2f}° to {float(lon.max().values):.2f}°")
        print()

    # Time information
    if 'time' in ds.coords:
        time = ds.coords['time']
        print("Time Information:")
        if len(time) > 0:
            print(f"  Start: {str(time[0].values)}")
            if len(time) > 1:
                print(f"  End: {str(time[-1].values)}")
                print(f"  Steps: {len(time)}")
        print()

    print("=" * 60)
    print()

    # Example code snippets
    print("Example Usage:")
    print()
    print("# Load the dataset")
    print("import xarray as xr")
    print(f"ds = xr.open_zarr('{zarr_path}')")
    print()
    print("# Access a variable")
    if len(ds.data_vars) > 0:
        example_var = list(ds.data_vars)[0]
        print(f"data = ds['{example_var}']")
        print()
        print("# Select a time step")
        print("data_t0 = data.isel(time=0)")
        print()
        print("# Plot (requires matplotlib)")
        print("# import matplotlib.pyplot as plt")
        print("# data_t0.plot()")
        print("# plt.show()")

    # Close dataset
    ds.close()

    print()
    print("✓ Dataset loaded successfully!")


if __name__ == '__main__':
    main()
