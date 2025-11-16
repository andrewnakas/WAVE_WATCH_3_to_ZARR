#!/usr/bin/env python3
"""
Download WAVE WATCH 3 data from NOAA NOMADS and convert to Zarr format.
"""

import os
import sys
from datetime import datetime, timedelta
import requests
from pathlib import Path
import xarray as xr
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_latest_run():
    """
    Determine the latest available WW3 run.
    Runs are at 00, 06, 12, 18 UTC.
    """
    now = datetime.utcnow()

    # Go back a few hours to ensure data is available
    # NOMADS typically has a delay of 3-4 hours
    safe_time = now - timedelta(hours=6)

    # Round down to nearest 6-hour cycle
    hour = (safe_time.hour // 6) * 6
    run_time = safe_time.replace(hour=hour, minute=0, second=0, microsecond=0)

    return run_time


def construct_download_url(run_time, forecast_hour=0):
    """
    Construct the NOMADS URL for WW3 global GRIB2 data.

    Args:
        run_time: datetime object for the model run
        forecast_hour: forecast hour (0, 3, 6, ..., 384)

    Returns:
        URL string
    """
    date_str = run_time.strftime('%Y%m%d')
    cycle = run_time.strftime('%H')

    # WW3 global gridded GRIB2 file pattern
    # Example: gfswave.t00z.global.0p16.f000.grib2
    filename = f"gfswave.t{cycle}z.global.0p16.f{forecast_hour:03d}.grib2"

    base_url = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
    url = f"{base_url}/gfs.{date_str}/{cycle}/wave/gridded/{filename}"

    return url, filename


def download_file(url, output_path, max_retries=3):
    """
    Download a file from URL with retry logic.

    Args:
        url: URL to download from
        output_path: Local path to save file
        max_retries: Maximum number of retry attempts

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading from {url} (attempt {attempt + 1}/{max_retries})")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"Downloaded {output_path.name} ({file_size:.2f} MB)")
            return True

        except requests.exceptions.RequestException as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying...")
            else:
                logger.error(f"Failed to download {url} after {max_retries} attempts")
                return False

    return False


def grib_to_zarr(grib_path, zarr_path):
    """
    Convert GRIB2 file to Zarr format.

    Args:
        grib_path: Path to input GRIB2 file
        zarr_path: Path to output Zarr directory
    """
    try:
        logger.info(f"Converting {grib_path} to Zarr format...")

        # Open GRIB2 file with cfgrib engine
        ds = xr.open_dataset(
            grib_path,
            engine='cfgrib',
            backend_kwargs={'indexpath': ''}
        )

        # Add metadata
        ds.attrs['source'] = 'NOAA NOMADS - WAVE WATCH III'
        ds.attrs['download_time'] = datetime.utcnow().isoformat()
        ds.attrs['original_file'] = grib_path.name

        # Remove existing zarr if it exists
        if zarr_path.exists():
            import shutil
            shutil.rmtree(zarr_path)

        # Save to Zarr
        zarr_path.parent.mkdir(parents=True, exist_ok=True)
        ds.to_zarr(zarr_path, mode='w')

        logger.info(f"Zarr dataset saved to {zarr_path}")

        # Print dataset info
        logger.info(f"Dataset variables: {list(ds.data_vars)}")
        logger.info(f"Dataset dimensions: {dict(ds.dims)}")

        ds.close()
        return True

    except Exception as e:
        logger.error(f"Error converting GRIB to Zarr: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""

    # Setup paths
    data_dir = Path(__file__).parent / 'data'
    grib_dir = data_dir / 'grib'
    zarr_dir = data_dir / 'zarr'

    # Get latest run time
    run_time = get_latest_run()
    logger.info(f"Fetching WW3 data for run: {run_time.strftime('%Y-%m-%d %H:%M UTC')}")

    # Download first forecast hour (analysis/nowcast - f000)
    url, filename = construct_download_url(run_time, forecast_hour=0)
    grib_path = grib_dir / filename

    # Download GRIB2 file
    if not download_file(url, grib_path):
        logger.error("Failed to download WW3 data")
        sys.exit(1)

    # Convert to Zarr
    run_id = run_time.strftime('%Y%m%d_%H')
    zarr_path = zarr_dir / f'ww3_global_{run_id}.zarr'

    if not grib_to_zarr(grib_path, zarr_path):
        logger.error("Failed to convert to Zarr")
        sys.exit(1)

    # Create a 'latest' symlink
    latest_link = zarr_dir / 'latest.zarr'
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(zarr_path.name)

    logger.info("✓ WW3 data download and conversion complete!")
    logger.info(f"  Run time: {run_time.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"  Zarr location: {zarr_path}")

    # Clean up old GRIB files to save space
    logger.info("Cleaning up GRIB files...")
    for grib_file in grib_dir.glob('*.grib2'):
        grib_file.unlink()
        logger.info(f"Removed {grib_file.name}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
