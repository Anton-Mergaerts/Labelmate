"""Resolve data directories for development and PyInstaller builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = 'Labelmate'


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def project_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    if is_frozen():
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        return base / APP_NAME
    return project_root()


def ensure_user_data() -> Path:
    root = user_data_dir()
    (root / 'data' / 'backups').mkdir(parents=True, exist_ok=True)
    (root / 'settings').mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return user_data_dir() / 'data' / 'labelmate.db'


def backup_dir() -> Path:
    return user_data_dir() / 'data' / 'backups'


def settings_path() -> Path:
    if is_frozen():
        return user_data_dir() / 'settings' / 'printer_settings.json'
    return project_root() / 'app_data' / 'settings' / 'printer_settings.json'


def prints_dir() -> Path:
    if is_frozen():
        return user_data_dir() / 'prints'
    return project_root() / 'app_data' / 'prints'


def logo_path() -> Path:
    return project_root() / 'assets' / 'kick_logo_1024-1.webp'
