#!/usr/bin/env python3
"""
Download WAVE WATCH 3 data from NOAA NOMADS and convert to Zarr format.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import requests
from pathlib import Path
import xarray as xr
import cfgrib
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
    Convert GRIB2 file to Zarr format, reading ALL GRIB messages.
    Filters out wind variables (u, v, ws, wdir) that are already in GFS.

    Args:
        grib_path: Path to input GRIB2 file
        zarr_path: Path to output Zarr directory
    """
    try:
        logger.info(f"Converting {grib_path} to Zarr format...")
        logger.info("Reading all GRIB messages (wave-specific variables only)...")

        # Open ALL datasets in the GRIB2 file
        # cfgrib.open_datasets returns a list of datasets for each hypercube
        datasets = cfgrib.open_datasets(
            str(grib_path),
            backend_kwargs={'indexpath': ''}
        )

        logger.info(f"Found {len(datasets)} GRIB message groups")

        if len(datasets) == 0:
            logger.error("No datasets found in GRIB file")
            return False

        # Merge all datasets
        # Strategy: merge datasets with same coordinates
        merged_ds = xr.merge(datasets, compat='override')

        # Filter out wind variables (already in standard GFS)
        wind_vars = ['u', 'v', 'ws', 'wdir']
        wave_vars = [var for var in merged_ds.data_vars if var not in wind_vars]
        merged_ds = merged_ds[wave_vars]

        logger.info(f"Kept {len(merged_ds.data_vars)} wave-specific variables (excluded wind: {wind_vars})")

        # Add metadata
        merged_ds.attrs['source'] = 'NOAA NOMADS - WAVE WATCH III'
        merged_ds.attrs['download_time'] = datetime.utcnow().isoformat()
        merged_ds.attrs['original_file'] = grib_path.name
        merged_ds.attrs['grib_messages'] = len(datasets)
        merged_ds.attrs['excluded_variables'] = 'u, v, ws, wdir (available in standard GFS)'

        # Remove existing zarr if it exists
        if zarr_path.exists():
            import shutil
            shutil.rmtree(zarr_path)

        # Save to Zarr
        zarr_path.parent.mkdir(parents=True, exist_ok=True)
        merged_ds.to_zarr(zarr_path, mode='w')

        logger.info(f"Zarr dataset saved to {zarr_path}")

        # Print dataset info
        logger.info(f"Dataset variables: {sorted(list(merged_ds.data_vars))}")
        logger.info(f"Dataset dimensions: {dict(merged_ds.dims)}")

        # Print variable counts by type
        var_names = list(merged_ds.data_vars)
        logger.info(f"Total variables: {len(var_names)}")

        # Close datasets
        merged_ds.close()
        for ds in datasets:
            ds.close()

        return True

    except Exception as e:
        logger.error(f"Error converting GRIB to Zarr: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_forecast_hours(hours_str):
    """
    Parse forecast hours string into list of integers.
    Supports formats: '0', '0,3,6', '0-12', '0-12:3'

    Args:
        hours_str: String specifying forecast hours

    Returns:
        List of forecast hour integers
    """
    hours = []

    for part in hours_str.split(','):
        if '-' in part:
            # Range specification
            range_parts = part.split('-')
            start = int(range_parts[0])

            # Check for step size first
            if ':' in range_parts[1]:
                end_step = range_parts[1].split(':')
                end = int(end_step[0])
                step = int(end_step[1])
            else:
                end = int(range_parts[1])
                step = 1

            hours.extend(range(start, end + 1, step))
        else:
            hours.append(int(part))

    return sorted(set(hours))  # Remove duplicates and sort


def download_multiple_forecasts(run_time, forecast_hours, grib_dir):
    """
    Download multiple forecast hours and combine them.

    Args:
        run_time: Model run datetime
        forecast_hours: List of forecast hours to download
        grib_dir: Directory to save GRIB files

    Returns:
        List of downloaded GRIB file paths
    """
    grib_files = []

    for fhour in forecast_hours:
        url, filename = construct_download_url(run_time, forecast_hour=fhour)
        grib_path = grib_dir / filename

        if download_file(url, grib_path):
            grib_files.append(grib_path)
        else:
            logger.warning(f"Skipping forecast hour {fhour} due to download failure")

    return grib_files


def combine_forecasts_to_zarr(grib_files, zarr_path):
    """
    Convert multiple GRIB files to a single Zarr dataset using incremental writing.
    This processes one timestep at a time to avoid memory issues.

    Args:
        grib_files: List of GRIB file paths
        zarr_path: Output Zarr path
    """
    try:
        logger.info(f"Converting {len(grib_files)} GRIB files to Zarr format...")
        logger.info("Using incremental writing to manage memory...")

        # Remove existing zarr if it exists
        if zarr_path.exists():
            import shutil
            shutil.rmtree(zarr_path)

        zarr_path.parent.mkdir(parents=True, exist_ok=True)

        total_vars = 0

        processed_count = 0
        skipped_count = 0

        for idx, grib_file in enumerate(grib_files):
            if idx % 10 == 0:  # Log progress every 10 files
                logger.info(f"Processing file {idx + 1}/{len(grib_files)}: {grib_file.name}")

            try:
                # Validate file size (GRIB files should be > 1MB)
                file_size = grib_file.stat().st_size
                if file_size < 1_000_000:  # Less than 1MB is likely corrupt/incomplete
                    logger.warning(f"Skipping {grib_file.name} - file too small ({file_size} bytes)")
                    skipped_count += 1
                    continue

                # Read all messages from this GRIB file
                datasets = cfgrib.open_datasets(
                    str(grib_file),
                    backend_kwargs={'indexpath': ''}
                )

                # Merge messages within this file
                merged = xr.merge(datasets, compat='override')

                # Filter out wind variables (already in standard GFS)
                wind_vars = ['u', 'v', 'ws', 'wdir']
                wave_vars = [var for var in merged.data_vars if var not in wind_vars]
                merged = merged[wave_vars]

                # Add time coordinate if missing (expand to have time dimension)
                if 'time' not in merged.dims:
                    merged = merged.expand_dims('time')

                if processed_count == 0:
                    # First valid file: create the zarr store
                    total_vars = len(merged.data_vars)

                    # Add metadata
                    merged.attrs['source'] = 'NOAA NOMADS - WAVE WATCH III'
                    merged.attrs['download_time'] = datetime.utcnow().isoformat()
                    merged.attrs['num_files'] = len(grib_files)
                    merged.attrs['excluded_variables'] = 'u, v, ws, wdir (available in standard GFS)'

                    merged.to_zarr(zarr_path, mode='w', compute=True)
                    logger.info(f"Initialized Zarr with {total_vars} wave-specific variables")
                else:
                    # Subsequent files: append along time dimension
                    merged.to_zarr(zarr_path, mode='a', append_dim='time', compute=True)

                # Close datasets to free memory
                for ds in datasets:
                    ds.close()
                merged.close()

                # Free memory
                del merged
                del datasets

                processed_count += 1

                # Clean up GRIB file after successful processing to save disk space
                try:
                    grib_file.unlink()
                    logger.debug(f"Cleaned up {grib_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {grib_file.name}: {e}")

            except EOFError as e:
                logger.warning(f"Skipping corrupted file {grib_file.name}: {e}")
                skipped_count += 1
                # Try to clean up corrupted file
                try:
                    grib_file.unlink()
                except:
                    pass
                continue
            except Exception as e:
                logger.warning(f"Error processing {grib_file.name}: {e}")
                skipped_count += 1
                continue

        logger.info(f"Zarr dataset saved to {zarr_path}")
        logger.info(f"Successfully processed: {processed_count}/{len(grib_files)} files")
        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} corrupted/invalid files")

        if processed_count == 0:
            logger.error("No valid files were processed!")
            return False

        # Open final dataset to report stats
        final_ds = xr.open_zarr(zarr_path)
        logger.info(f"Dataset variables: {sorted(list(final_ds.data_vars))}")
        logger.info(f"Total variables: {len(final_ds.data_vars)}")
        logger.info(f"Time steps: {len(final_ds.time)}")
        final_ds.close()

        return True

    except Exception as e:
        logger.error(f"Error combining forecasts to Zarr: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Download WAVE WATCH III data and convert to Zarr format'
    )
    parser.add_argument(
        '--forecast-hours',
        default=os.environ.get('WW3_FORECAST_HOURS', '0'),
        help='Forecast hours to download. Examples: "0", "0,3,6", "0-24:3" (default: 0)'
    )
    args = parser.parse_args()

    # Setup paths
    data_dir = Path(__file__).parent / 'data'
    grib_dir = data_dir / 'grib'
    zarr_dir = data_dir / 'zarr'

    # Get latest run time
    run_time = get_latest_run()
    logger.info(f"Fetching WW3 data for run: {run_time.strftime('%Y-%m-%d %H:%M UTC')}")

    # Parse forecast hours
    forecast_hours = parse_forecast_hours(args.forecast_hours)
    logger.info(f"Forecast hours to download: {forecast_hours}")

    # Download GRIB files
    if len(forecast_hours) == 1:
        # Single forecast hour - use simple method
        url, filename = construct_download_url(run_time, forecast_hour=forecast_hours[0])
        grib_path = grib_dir / filename

        if not download_file(url, grib_path):
            logger.error("Failed to download WW3 data")
            sys.exit(1)

        # Convert to Zarr
        run_id = run_time.strftime('%Y%m%d_%H')
        zarr_path = zarr_dir / f'ww3_global_{run_id}.zarr'

        if not grib_to_zarr(grib_path, zarr_path):
            logger.error("Failed to convert to Zarr")
            sys.exit(1)
    else:
        # Multiple forecast hours - download and combine
        grib_files = download_multiple_forecasts(run_time, forecast_hours, grib_dir)

        if not grib_files:
            logger.error("No GRIB files downloaded")
            sys.exit(1)

        run_id = run_time.strftime('%Y%m%d_%H')
        fhour_range = f"f{min(forecast_hours):03d}-f{max(forecast_hours):03d}"
        zarr_path = zarr_dir / f'ww3_global_{run_id}_{fhour_range}.zarr'

        if not combine_forecasts_to_zarr(grib_files, zarr_path):
            logger.error("Failed to convert to Zarr")
            sys.exit(1)

    # Create a 'latest' symlink
    latest_link = zarr_dir / 'latest.zarr'
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(zarr_path.name)

    logger.info("✓ WW3 data download and conversion complete!")
    logger.info(f"  Run time: {run_time.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"  Forecast hours: {forecast_hours}")
    logger.info(f"  Zarr location: {zarr_path}")

    # Clean up old GRIB files to save space
    logger.info("Cleaning up GRIB files...")
    for grib_file in grib_dir.glob('*.grib2'):
        grib_file.unlink()
        logger.info(f"Removed {grib_file.name}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
