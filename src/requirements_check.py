"""Startup and runtime checks for Labelmate dependencies and printer setup."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from src import paths


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # ok | warn | fail
    message: str
    hint: str = ''

    @property
    def ok(self) -> bool:
        return self.status == 'ok'

    @property
    def blocking(self) -> bool:
        return self.status == 'fail'


def _ok(name: str, message: str) -> CheckResult:
    return CheckResult(name, 'ok', message)


def _warn(name: str, message: str, hint: str = '') -> CheckResult:
    return CheckResult(name, 'warn', message, hint)


def _fail(name: str, message: str, hint: str = '') -> CheckResult:
    return CheckResult(name, 'fail', message, hint)


def check_platform() -> CheckResult:
    if sys.platform == 'win32':
        return _ok('Windows', 'Running on Windows.')
    return _fail(
        'Windows',
        f'Labelmate printing requires Windows (detected: {sys.platform}).',
        'Install and run Labelmate on a Windows PC with the Brother driver.',
    )


def check_python_packages() -> list[CheckResult]:
    if paths.is_frozen():
        return [_ok('Application bundle', 'Labelmate executable includes required libraries.')]

    results: list[CheckResult] = []
    packages = (
        ('PySide6', 'PySide6'),
        ('PIL', 'pillow'),
        ('win32print', 'pywin32'),
        ('brother_ql', 'brother-ql'),
    )
    for module_name, pip_name in packages:
        try:
            __import__(module_name)
            results.append(_ok(f'Package: {pip_name}', f'{pip_name} is installed.'))
        except ImportError as exc:
            results.append(
                _fail(
                    f'Package: {pip_name}',
                    f'{pip_name} is missing ({exc}).',
                    f'Run: pip install -r requirements.txt',
                )
            )
    return results


def check_data_directories() -> CheckResult:
    try:
        root = paths.ensure_user_data()
        test_file = root / 'settings' / '.write_test'
        test_file.write_text('ok', encoding='utf-8')
        test_file.unlink(missing_ok=True)
        location = root
        if paths.is_frozen():
            detail = f'Data folder ready at {location}'
        else:
            detail = f'Project data folder ready at {location}'
        return _ok('Data storage', detail)
    except OSError as exc:
        return _fail(
            'Data storage',
            f'Cannot write application data: {exc}',
            f'Check permissions for {paths.user_data_dir()}',
        )


def check_label_fonts() -> CheckResult:
    candidates = (
        Path('C:/Windows/Fonts/segoeuib.ttf'),
        Path('C:/Windows/Fonts/segoeui.ttf'),
        Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
    )
    found = next((path.name for path in candidates if path.exists()), None)
    if found:
        return _ok('Label fonts', f'Using Windows font: {found}')
    return _warn(
        'Label fonts',
        'Segoe UI / Arial fonts were not found; labels may use a smaller fallback font.',
    )


def check_brother_printer() -> CheckResult:
    if sys.platform != 'win32':
        return _warn('Brother printer', 'Printer detection skipped (not on Windows).')

    try:
        from src import printing

        name = printing.find_brother_printer()
        if name:
            return _ok('Brother printer', f'Found in Windows: {name}')
        return _fail(
            'Brother printer',
            'No Brother QL printer found in Windows.',
            'Add the printer in Settings using the official Brother QL-820 driver.',
        )
    except Exception as exc:
        return _fail('Brother printer', f'Could not list printers: {exc}')


def check_printer_driver() -> CheckResult:
    if sys.platform != 'win32':
        return _warn('Printer driver', 'Driver check skipped (not on Windows).')

    try:
        from app_data.settings import printer_store
        from src import printing

        settings = printer_store.load_settings()
        printer_name = settings.get('conn', '').strip() or printing.find_brother_printer()
        if not printer_name:
            return _warn(
                'Printer driver',
                'No printer selected yet.',
                'Open Printer Settings and choose your Brother printer.',
            )

        driver = printing.get_printer_driver(printer_name)
        if printing.uses_ipp_driver(printer_name):
            return _fail(
                'Printer driver',
                f'"{printer_name}" uses {driver}.',
                printing.BROTHER_DRIVER_HELP,
            )
        return _ok('Printer driver', f'{printer_name} · {driver}')
    except Exception as exc:
        return _warn('Printer driver', f'Could not verify driver: {exc}')


def check_printer_settings() -> CheckResult:
    from app_data.settings import printer_store

    settings = printer_store.load_settings()
    printer_name = settings.get('conn', '').strip()
    label_size = settings.get('label_size', '').strip()

    if not printer_name:
        return _warn(
            'Printer settings',
            'No Windows printer selected.',
            'Open Printer Settings and pick your Brother QL-820NWB.',
        )
    if not label_size:
        return _warn(
            'Printer settings',
            'Label roll type is not set.',
            'Choose the roll that matches your tape (DK-44205 = 62 mm black/white).',
        )
    return _ok(
        'Printer settings',
        f'{printer_name} · roll {label_size}',
    )


def check_catalog() -> CheckResult:
    from src import db

    brands = db.get_brands()
    if brands:
        return _ok('Label catalog', f'{len(brands)} brand(s) ready.')
    return _warn(
        'Label catalog',
        'The catalog is empty.',
        'Open Database Manager to add brands, models, and sizes.',
    )


def run_all_checks() -> list[CheckResult]:
    results: list[CheckResult] = [
        check_platform(),
        check_data_directories(),
        *check_python_packages(),
        check_label_fonts(),
        check_brother_printer(),
        check_printer_driver(),
        check_printer_settings(),
        check_catalog(),
    ]
    return results


def summarize(results: list[CheckResult]) -> tuple[int, int, int]:
    ok = sum(1 for item in results if item.status == 'ok')
    warn = sum(1 for item in results if item.status == 'warn')
    fail = sum(1 for item in results if item.status == 'fail')
    return ok, warn, fail


def can_print(results: list[CheckResult] | None = None) -> bool:
    results = results or run_all_checks()
    blockers = {
        'Windows',
        'Brother printer',
        'Printer driver',
    }
    for item in results:
        if item.name in blockers and item.blocking:
            return False
        if item.name.startswith('Package:') and item.blocking:
            return False
    return True


def blocking_messages(results: list[CheckResult]) -> list[str]:
    return [item.message for item in results if item.blocking]
