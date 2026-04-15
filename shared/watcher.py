#!/usr/bin/env python3
"""
SPCOCATOR Auto-Watcher — Phase 3

Monitors folders for new .pdf, .bin, and .cal files.
On detection:
  - .pdf/.bin → re-runs extract_and_parse.py + generate_dashboard.py
  - .cal      → runs cal cert generator on the new file

Usage:
  python3 shared/watcher.py                    # uses watcher_config.json
  python3 shared/watcher.py --config path.json # custom config
  python3 shared/watcher.py --once             # process existing files and exit
"""

import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Timer

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_DIR / "watcher_config.json"
PROCESSED_MANIFEST = PROJECT_DIR / "logs" / "processed_files.json"

# Scripts
EXTRACT_SCRIPT = PROJECT_DIR / "tools" / "extract_and_parse.py"
DASHBOARD_SCRIPT = PROJECT_DIR / "generate_dashboard.py"
CAL_CERT_SCRIPT = PROJECT_DIR / "modules" / "cal_certs" / "generate_cert.py"

logger = logging.getLogger("spcocator-watcher")


def setup_logging(config: dict):
    """Configure rotating file + console logging."""
    log_path = PROJECT_DIR / config.get("log_file", "logs/watcher.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(
        log_path,
        maxBytes=config.get("log_max_bytes", 5 * 1024 * 1024),
        backupCount=config.get("log_backup_count", 3),
    )
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

    logger.info("Log file: %s", log_path)


def load_config(path: Path = None) -> dict:
    """Load watcher_config.json."""
    path = path or DEFAULT_CONFIG
    with open(path) as f:
        return json.load(f)


def run_script(script: Path, args: list = None) -> bool:
    """Run a Python script, return True on success."""
    cmd = [sys.executable, str(script)] + (args or [])
    logger.info("  Running: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(PROJECT_DIR))
        if result.returncode == 0:
            # Log last few lines of stdout for context
            out_lines = result.stdout.strip().split("\n")
            for line in out_lines[-5:]:
                if line.strip():
                    logger.info("    %s", line.strip())
            return True
        else:
            logger.error("  Script failed (exit %d): %s", result.returncode, result.stderr.strip()[:500])
            return False
    except subprocess.TimeoutExpired:
        logger.error("  Script timed out after 300s: %s", script.name)
        return False
    except Exception as e:
        logger.error("  Script error: %s", e)
        return False


def sync_files(files: list, dest_dir: str):
    """Copy files to a local directory if they don't already exist or are newer."""
    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    synced = 0
    for src_path in files:
        src = Path(src_path)
        dst = dest / src.name
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
            logger.info("  Synced: %s -> %s", src.name, dest)
            synced += 1
    if synced:
        logger.info("  Synced %d file(s) to %s", synced, dest)
    return synced


def action_dashboard():
    """Re-extract PDFs and regenerate the SPC dashboard."""
    logger.info("ACTION: Dashboard regeneration")
    ok1 = run_script(EXTRACT_SCRIPT)
    ok2 = run_script(DASHBOARD_SCRIPT)
    if ok1 and ok2:
        logger.info("ACTION: Dashboard regeneration complete")
    else:
        logger.warning("ACTION: Dashboard regeneration had errors")
    return ok1 and ok2


def action_cal_cert(cal_file: str = None):
    """Generate a cal cert for a specific .cal file (or all if none specified)."""
    logger.info("ACTION: Cal cert generation")
    args = [cal_file] if cal_file else []
    ok = run_script(CAL_CERT_SCRIPT, args)
    if ok:
        logger.info("ACTION: Cal cert generation complete")
    else:
        logger.warning("ACTION: Cal cert generation had errors")
    return ok


def copy_output(config: dict):
    """Copy generated output to ATORcloud (if configured)."""
    dashboard_dest = config.get("output", {}).get("dashboard_copy_to", "")
    certs_dest = config.get("output", {}).get("cal_certs_copy_to", "")

    if dashboard_dest:
        dest = Path(dashboard_dest).expanduser()
        src = PROJECT_DIR / "OMNIcheck_SPC_Dashboard.html"
        if src.exists() and dest.parent.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            logger.info("  Copied dashboard -> %s", dest)

    if certs_dest:
        dest_dir = Path(certs_dest).expanduser()
        src_dir = PROJECT_DIR / "output" / "cal_certs"
        if src_dir.exists() and dest_dir.parent.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            for cert in src_dir.glob("*.html"):
                shutil.copy2(cert, dest_dir / cert.name)
            logger.info("  Copied cal certs -> %s", dest_dir)


class DebouncedHandler(FileSystemEventHandler):
    """
    Debounced file event handler.

    Accumulates file creation/modification events and fires the appropriate
    action after a quiet period (debounce_seconds). This prevents re-running
    the pipeline multiple times when several files land at once.
    """

    def __init__(self, watch_entry: dict, config: dict):
        super().__init__()
        self.watch_name = watch_entry["name"]
        self.extensions = set(watch_entry["extensions"])
        self.action_type = watch_entry["action"]
        self.debounce = config.get("debounce_seconds", 5)
        self.sync_to = watch_entry.get("sync_to", "")
        self.config = config
        self._timer = None
        self._pending_files = []

    def _matches(self, path: str) -> bool:
        return Path(path).suffix.lower() in self.extensions

    def on_created(self, event):
        if event.is_directory or not self._matches(event.src_path):
            return
        self._schedule(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not self._matches(event.src_path):
            return
        self._schedule(event.src_path)

    def _schedule(self, filepath: str):
        if filepath not in self._pending_files:
            self._pending_files.append(filepath)
            logger.info("[%s] Detected: %s", self.watch_name, Path(filepath).name)

        # Reset debounce timer
        if self._timer:
            self._timer.cancel()
        self._timer = Timer(self.debounce, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self):
        files = self._pending_files[:]
        self._pending_files.clear()

        logger.info("[%s] Processing %d file(s) after %.0fs debounce", self.watch_name, len(files), self.debounce)

        if self.action_type == "dashboard":
            action_dashboard()
        elif self.action_type == "sync_and_dashboard":
            if self.sync_to:
                sync_files(files, self.sync_to)
            action_dashboard()
        elif self.action_type == "cal_cert":
            for f in files:
                action_cal_cert(f)

        # Record processed files in manifest
        manifest = load_manifest()
        record_processed(files, manifest)

        copy_output(self.config)


def load_manifest() -> dict:
    """Load the processed-files manifest. Returns {filepath: mtime_float}."""
    if PROCESSED_MANIFEST.exists():
        with open(PROCESSED_MANIFEST) as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict):
    """Save the processed-files manifest."""
    PROCESSED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


def record_processed(filepaths: list, manifest: dict):
    """Mark files as processed in the manifest and save."""
    for fp in filepaths:
        p = Path(fp)
        if p.exists():
            manifest[str(p)] = p.stat().st_mtime
    save_manifest(manifest)


def startup_scan(config: dict):
    """Scan all watch folders for files missed while the watcher was not running.

    Compares current folder contents against the processed-files manifest.
    Any file that is new (not in manifest) or modified (mtime changed) triggers
    the appropriate action.
    """
    logger.info("Startup scan: checking for files missed while offline...")
    manifest = load_manifest()
    need_dashboard = False
    new_cal_files = []

    for entry in config.get("watch", []):
        watch_path = Path(entry["path"]).expanduser()
        if not watch_path.exists():
            continue

        extensions = set(entry["extensions"])
        for ext in extensions:
            for filepath in watch_path.glob(f"*{ext}"):
                key = str(filepath)
                current_mtime = filepath.stat().st_mtime
                prev_mtime = manifest.get(key)

                if prev_mtime is None or current_mtime != prev_mtime:
                    logger.info("  New/modified: %s", filepath.name)
                    if entry["action"] in ("dashboard", "sync_and_dashboard"):
                        need_dashboard = True
                        # Sync file to local if configured
                        sync_to = entry.get("sync_to", "")
                        if sync_to:
                            sync_files([key], sync_to)
                    elif entry["action"] == "cal_cert":
                        new_cal_files.append(key)

    if not need_dashboard and not new_cal_files:
        logger.info("Startup scan: everything up to date")
        # Still record current state so first run seeds the manifest
        _seed_manifest(config, manifest)
        return

    if need_dashboard:
        logger.info("Startup scan: %s", "new/modified PDF or .bin files found — regenerating dashboard")
        action_dashboard()
        # Record all current dashboard-related files
        for entry in config.get("watch", []):
            if entry["action"] in ("dashboard", "sync_and_dashboard"):
                watch_path = Path(entry["path"]).expanduser()
                if watch_path.exists():
                    for ext in entry["extensions"]:
                        record_processed([str(f) for f in watch_path.glob(f"*{ext}")], manifest)

    if new_cal_files:
        logger.info("Startup scan: %d new/modified .cal file(s) found", len(new_cal_files))
        for cal_file in new_cal_files:
            action_cal_cert(cal_file)
        record_processed(new_cal_files, manifest)

    copy_output(config)
    logger.info("Startup scan complete")


def _seed_manifest(config: dict, manifest: dict):
    """Record current state of all watched files into the manifest."""
    changed = False
    for entry in config.get("watch", []):
        watch_path = Path(entry["path"]).expanduser()
        if not watch_path.exists():
            continue
        for ext in entry["extensions"]:
            for filepath in watch_path.glob(f"*{ext}"):
                key = str(filepath)
                current_mtime = filepath.stat().st_mtime
                if manifest.get(key) != current_mtime:
                    manifest[key] = current_mtime
                    changed = True
    if changed:
        save_manifest(manifest)


def start_watching(config: dict):
    """Start watchdog observers for all configured watch paths."""
    observer = Observer()
    active_watches = []

    for entry in config.get("watch", []):
        watch_path = Path(entry["path"]).expanduser()
        if not watch_path.exists():
            logger.warning("Watch path does not exist, skipping: %s (%s)", watch_path, entry["name"])
            continue

        handler = DebouncedHandler(entry, config)
        observer.schedule(handler, str(watch_path), recursive=entry.get("recursive", False))
        active_watches.append(entry["name"])
        logger.info("Watching: %s -> %s [%s]", entry["name"], watch_path, ", ".join(entry["extensions"]))

    if not active_watches:
        logger.error("No valid watch paths configured. Exiting.")
        return

    # Catch up on files missed while offline before starting real-time monitoring
    startup_scan(config)

    observer.start()
    logger.info("SPCOCATOR watcher started — %d folder(s) monitored", len(active_watches))
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        observer.stop()
    observer.join()
    logger.info("Watcher stopped.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SPCOCATOR auto-watcher")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to watcher_config.json")
    parser.add_argument("--once", action="store_true", help="Run all actions once and exit (no watching)")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)

    logger.info("=" * 60)
    logger.info("SPCOCATOR Watcher — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    if args.once:
        logger.info("--once mode: running all actions and exiting")
        # Sync cloud files to local before extraction
        for entry in config.get("watch", []):
            if entry["action"] == "sync_and_dashboard" and entry.get("sync_to"):
                watch_path = Path(entry["path"]).expanduser()
                if watch_path.exists():
                    files = []
                    for ext in entry["extensions"]:
                        files.extend(str(f) for f in watch_path.glob(f"*{ext}"))
                    if files:
                        sync_files(files, entry["sync_to"])
        action_dashboard()
        # Process all existing .cal files
        for entry in config.get("watch", []):
            if entry["action"] == "cal_cert":
                cal_dir = Path(entry["path"]).expanduser()
                if cal_dir.exists():
                    for cal_file in sorted(cal_dir.glob("*.cal")):
                        action_cal_cert(str(cal_file))
        copy_output(config)
        # Seed the manifest so future startups know what's already processed
        manifest = load_manifest()
        _seed_manifest(config, manifest)
        logger.info("Manifest seeded with %d files", len(manifest))
        logger.info("Done.")
        return

    start_watching(config)


if __name__ == "__main__":
    main()
