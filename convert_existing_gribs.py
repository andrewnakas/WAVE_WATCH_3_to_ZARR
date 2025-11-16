#!/usr/bin/env python3
"""Convert existing GRIB files to Zarr using incremental writing."""

import sys
from pathlib import Path
import logging

# Import from the main script
from download_ww3 import combine_forecasts_to_zarr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Get all GRIB files
    grib_dir = Path('data/grib')
    grib_files = sorted(grib_dir.glob('*.grib2'))

    logger.info(f"Found {len(grib_files)} GRIB files to convert")

    if not grib_files:
        logger.error("No GRIB files found in data/grib/")
        sys.exit(1)

    # Output path
    zarr_dir = Path('data/zarr')
    zarr_path = zarr_dir / 'ww3_global_20251116_00_f000-f384.zarr'

    # Convert using incremental writing
    success = combine_forecasts_to_zarr(grib_files, zarr_path)

    if success:
        # Update latest symlink
        latest_link = zarr_dir / 'latest.zarr'
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(zarr_path.name)

        logger.info("✓ Conversion complete!")
        logger.info(f"  Zarr location: {zarr_path}")
    else:
        logger.error("Conversion failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
