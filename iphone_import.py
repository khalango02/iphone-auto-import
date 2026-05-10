#!/usr/bin/env python3
"""Daemon that auto-imports new iPhone photos/videos to Photos.app when device is connected."""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
IMPORTED_LOG = Path.home() / ".iphone_imported.json"
POLL_INTERVAL = 5          # seconds between device checks
DELETE_AFTER_IMPORT = True  # delete from iPhone after successful import
MEDIA_EXTENSIONS = {
    '.jpg', '.jpeg', '.heic', '.heif', '.png', '.gif',
    '.tiff', '.raw', '.dng', '.braw',
    '.mp4', '.mov', '.m4v',
}
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)


def load_imported() -> set:
    if IMPORTED_LOG.exists():
        try:
            return set(json.loads(IMPORTED_LOG.read_text()))
        except Exception:
            return set()
    return set()


def save_imported(imported: set) -> None:
    IMPORTED_LOG.write_text(json.dumps(sorted(imported), indent=2))


def import_to_photos(file_path: str) -> bool:
    escaped = file_path.replace('"', '\\"')
    script = f'tell application "Photos" to import {{POSIX file "{escaped}"}}'
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        log.error("Photos.app import error: %s", result.stderr.strip())
    return result.returncode == 0


async def delete_from_device(afc, remote_path: str) -> bool:
    try:
        await afc.rm(remote_path)
        return True
    except Exception as e:
        log.warning("Could not delete %s from device: %s", os.path.basename(remote_path), e)
        return False


async def list_dcim_files(afc) -> list:
    files = []
    try:
        rolls = await afc.listdir('/DCIM')
    except Exception:
        return files

    for roll in rolls:
        roll_path = f'/DCIM/{roll}'
        try:
            for fname in await afc.listdir(roll_path):
                if Path(fname).suffix.lower() in MEDIA_EXTENSIONS:
                    files.append(f'{roll_path}/{fname}')
        except Exception:
            continue

    return files


async def process_device() -> None:
    try:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.afc import AfcService
    except ImportError:
        log.error("pymobiledevice3 not installed — run setup.sh first.")
        await asyncio.sleep(60)
        return

    try:
        lockdown = await create_using_usbmux(autopair=True)
    except Exception:
        return  # no device connected

    device_name = lockdown.display_name or lockdown.udid
    log.info("iPhone detected: %s", device_name)

    try:
        async with AfcService(lockdown) as afc:
            imported = load_imported()
            all_files = await list_dcim_files(afc)
            new_files = [f for f in all_files if f not in imported]

            if not new_files:
                log.info("No new media to import from %s", device_name)
                return

            log.info(
                "Importing %d new file(s) from %s%s",
                len(new_files),
                device_name,
                " (will delete after import)" if DELETE_AFTER_IMPORT else "",
            )

            with tempfile.TemporaryDirectory(prefix='iphone_import_') as tmp:
                for remote_path in new_files:
                    fname = os.path.basename(remote_path)
                    local_path = os.path.join(tmp, fname)
                    try:
                        data = await afc.get_file_contents(remote_path)
                        with open(local_path, 'wb') as f:
                            f.write(data)

                        if import_to_photos(local_path):
                            imported.add(remote_path)
                            if DELETE_AFTER_IMPORT:
                                deleted = await delete_from_device(afc, remote_path)
                                log.info("  ✓ %s%s", fname, " (deleted from iPhone)" if deleted else "")
                            else:
                                log.info("  ✓ %s", fname)
                        else:
                            log.warning("  ✗ %s (Photos.app rejected — keeping on device)", fname)
                    except Exception as e:
                        log.error("  ✗ %s: %s", fname, e)

            save_imported(imported)
            log.info("Import complete")

    except Exception as e:
        log.warning("Device session error: %s", e)


async def main_loop():
    log.info(
        "iPhone import daemon started (interval: %ds, delete after import: %s)",
        POLL_INTERVAL,
        DELETE_AFTER_IMPORT,
    )
    while True:
        await process_device()
        await asyncio.sleep(POLL_INTERVAL)


def main():
    asyncio.run(main_loop())


if __name__ == '__main__':
    main()
