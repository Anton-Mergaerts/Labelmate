import json
from datetime import datetime

from src.paths import prints_dir, settings_path

DEFAULT_SETTINGS = {
    'type': 'windows',
    'conn': '',
    'model': 'QL-820NWB',
    'label_size': '62',
    'text_scale': 'large',
    'show_logo': True,
    'footer_spacing': 'normal',
    'scan_to_print': True,
}


def load_settings():
    path = settings_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                merged = dict(DEFAULT_SETTINGS)
                merged.update(data)
                return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(settings, handle, indent=2, sort_keys=True)


def _printer_name_from_settings(settings: dict) -> str:
    conn = settings.get('conn', '').strip()
    if conn.startswith('usb://'):
        return settings.get('win_printer', '').strip()
    return conn or settings.get('win_printer', '').strip()


def ensure_printer_configured():
    settings = load_settings()
    changed = False

    if settings.get('type') != 'windows':
        settings['type'] = 'windows'
        changed = True

    if not settings.get('label_size'):
        settings['label_size'] = '62'
        changed = True

    if settings.get('text_scale') != 'large':
        settings['text_scale'] = 'large'
        changed = True

    if not isinstance(settings.get('show_logo'), bool):
        settings['show_logo'] = True
        changed = True

    if settings.get('footer_spacing') not in ('tight', 'normal', 'loose'):
        settings['footer_spacing'] = 'normal'
        changed = True

    if not isinstance(settings.get('scan_to_print'), bool):
        settings['scan_to_print'] = True
        changed = True

    conn = settings.get('conn', '').strip()
    if conn.startswith('usb://'):
        settings['conn'] = ''
        changed = True

    try:
        from src.printing import find_brother_printer, resolve_printer_name

        printer = _printer_name_from_settings(settings) or find_brother_printer()
        if printer:
            resolved = resolve_printer_name(printer)
            if settings.get('conn') != resolved:
                settings['conn'] = resolved
                changed = True
    except Exception:
        pass

    if changed:
        save_settings(settings)
    return settings


def save_print_artifact(brand, model, size, settings, mode='simulated'):
    target_dir = prints_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = target_dir / f'label-{timestamp}.txt'
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('Label job\n')
        handle.write('=========\n')
        handle.write(f'Mode: {mode}\n')
        handle.write(f'Brand: {brand}\n')
        handle.write(f'Model: {model}\n')
        handle.write(f'Size: {size}\n')
        handle.write('\nPrinter settings:\n')
        handle.write(json.dumps(settings, indent=2, sort_keys=True))
        handle.write('\n')
    return path
