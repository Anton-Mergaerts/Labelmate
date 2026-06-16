"""Render labels and print silently via the Brother Windows driver (RAW)."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PRINTABLE_WIDTH_PX = 696
TAPE_WIDTH_PX = 732
DEFAULT_LABEL_HEIGHT_PX = 220
MARGIN = 24
LINE_GAP = 10
DIVIDER_GAP = 10
RIGHT_COLUMN_MIN_PX = 190
COLUMN_GAP = 20

LABEL_ROLLS = {
    '62red': {'name': '62 mm black/red endless (demo roll)', 'red': True},
    '62': {'name': '62 mm black/white endless (DK-44205 paper)', 'red': False},
    '62x100': {'name': '62 mm x 100 mm die-cut', 'red': False},
    '62x29': {'name': '62 mm x 29 mm die-cut', 'red': False},
}

BROTHER_DRIVER_HELP = (
    'Install the official Brother QL-820 driver from brother.com, then add the printer '
    'in Windows Settings. The Microsoft IPP driver cannot print Labelmate labels.'
)


def _require_windows():
    if sys.platform != 'win32':
        raise RuntimeError('Printing is supported on Windows only.')


def list_installed_printers() -> list[str]:
    _require_windows()
    import win32print

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [entry[2] for entry in win32print.EnumPrinters(flags)]


def find_brother_printer() -> str | None:
    for name in list_installed_printers():
        lowered = name.lower()
        if 'brother' in lowered or 'ql-' in lowered or 'ql ' in lowered:
            return name
    return None


def get_printer_driver(printer_name: str) -> str:
    _require_windows()
    import win32print

    handle = win32print.OpenPrinter(printer_name)
    try:
        info = win32print.GetPrinter(handle, 2)
        return info.get('pDriverName', '') or ''
    finally:
        win32print.ClosePrinter(handle)


def uses_ipp_driver(printer_name: str) -> bool:
    driver = get_printer_driver(printer_name).lower()
    return 'ipp class driver' in driver or driver.startswith('microsoft')


def printer_driver_warning(printer_name: str) -> str | None:
    if uses_ipp_driver(printer_name):
        return f'"{printer_name}" uses {get_printer_driver(printer_name)}. {BROTHER_DRIVER_HELP}'
    return None


def resolve_printer_name(preferred: str = '') -> str:
    preferred = preferred.strip()
    if preferred and not preferred.startswith('usb://'):
        installed = set(list_installed_printers())
        if preferred in installed:
            return preferred
        raise RuntimeError(
            f'Printer "{preferred}" was not found. Open Printer Settings and pick an installed printer.'
        )

    brother = find_brother_printer()
    if brother:
        return brother

    raise RuntimeError(
        'No Brother printer found in Windows. Add the printer using the Brother QL-820 driver.'
    )


def printer_status(preferred: str = '') -> dict:
    status = {'printer': None, 'driver': None, 'driver_ok': False, 'error': None}
    try:
        name = resolve_printer_name(preferred)
        status['printer'] = name
        status['driver'] = get_printer_driver(name)
        status['driver_ok'] = not uses_ipp_driver(name)
    except RuntimeError as exc:
        status['error'] = str(exc)
    return status


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        candidates = (
            Path('C:/Windows/Fonts/segoeuib.ttf'),
            Path('C:/Windows/Fonts/arialbd.ttf'),
            Path('C:/Windows/Fonts/segoeui.ttf'),
            Path('C:/Windows/Fonts/arial.ttf'),
        )
    else:
        candidates = (
            Path('C:/Windows/Fonts/segoeui.ttf'),
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('C:/Windows/Fonts/segoeuib.ttf'),
        )
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    start_size: int,
    min_size: int,
    bold: bool = False,
):
    size = start_size
    while size >= min_size:
        font = _load_font(size, bold=bold)
        width, _ = _text_size(draw, text, font)
        if width <= max_width:
            return font
        size -= 2
    return _load_font(min_size, bold=bold)


def _label_height(label_size: str) -> tuple[int, str]:
    if label_size == '62x100':
        return 346, 'large'
    if label_size == '62x29':
        return 100, 'compact'
    return DEFAULT_LABEL_HEIGHT_PX, 'large'


def _text_height(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    _, height = _text_size(draw, text, font)
    return height


def render_label(brand: str, model: str, size: str, label_size: str = '62') -> Image.Image:
    height, layout = _label_height(label_size)
    margin = 14 if layout == 'compact' else MARGIN
    line_gap = 4 if layout == 'compact' else LINE_GAP
    divider_gap = 5 if layout == 'compact' else DIVIDER_GAP
    right_min = 88 if layout == 'compact' else RIGHT_COLUMN_MIN_PX
    column_gap = 10 if layout == 'compact' else COLUMN_GAP

    image = Image.new('RGB', (PRINTABLE_WIDTH_PX, height), 'white')
    draw = ImageDraw.Draw(image)

    if layout == 'compact':
        size_font = _fit_font(
            draw, size, max_width=right_min, start_size=34, min_size=22, bold=True,
        )
        brand_font = _fit_font(
            draw,
            brand,
            max_width=PRINTABLE_WIDTH_PX - margin * 2 - right_min - column_gap,
            start_size=24,
            min_size=16,
            bold=True,
        )
        model_font = _fit_font(
            draw,
            model,
            max_width=PRINTABLE_WIDTH_PX - margin * 2,
            start_size=18,
            min_size=14,
        )
    else:
        size_font = _fit_font(
            draw, size, max_width=right_min, start_size=64, min_size=40, bold=True,
        )
        brand_font = _fit_font(
            draw,
            brand,
            max_width=PRINTABLE_WIDTH_PX - margin * 2 - right_min - column_gap,
            start_size=56,
            min_size=32,
            bold=True,
        )
        model_font = _fit_font(
            draw,
            model,
            max_width=PRINTABLE_WIDTH_PX - margin * 2,
            start_size=38,
            min_size=24,
        )

    size_w, size_h = _text_size(draw, size, size_font)
    _, brand_h = _text_size(draw, brand, brand_font)
    _, model_h = _text_size(draw, model, model_font)

    header_h = max(brand_h, size_h)
    block_h = header_h + divider_gap + 1 + 8 + model_h
    y = max(margin, (height - block_h) // 2)

    size_x = PRINTABLE_WIDTH_PX - margin - size_w
    brand_y = y + (header_h - brand_h) // 2
    size_y = y + (header_h - size_h) // 2

    draw.text((margin, brand_y), brand, fill='black', font=brand_font)
    draw.text((size_x, size_y), size, fill='black', font=size_font)

    rule_y = y + header_h + divider_gap
    draw.line((margin, rule_y, PRINTABLE_WIDTH_PX - margin, rule_y), fill='#c8d0dc', width=1)

    model_y = rule_y + 8
    draw.text((margin, model_y), model, fill='black', font=model_font)

    return image


def build_raster_data(
    image: Image.Image,
    *,
    ql_model: str = 'QL-820NWB',
    label_size: str = '62',
    red: bool = True,
) -> bytes:
    from brother_ql.conversion import convert
    from brother_ql.raster import BrotherQLRaster

    qlr = BrotherQLRaster(ql_model)
    convert(qlr, [image], label_size, rotate='0', red=red, cut=True)
    return bytes(qlr.data)


def clear_stuck_jobs(printer_name: str) -> int:
    """Cancel stale spooler jobs that make the Brother driver show communication popups."""
    _require_windows()
    import win32print

    stuck_flags = (
        win32print.JOB_STATUS_ERROR
        | win32print.JOB_STATUS_OFFLINE
        | win32print.JOB_STATUS_BLOCKED_DEVQ
        | win32print.JOB_STATUS_USER_INTERVENTION
        | win32print.JOB_STATUS_DELETING
    )
    cleared = 0
    handle = win32print.OpenPrinter(printer_name)
    if not handle:
        return 0
    try:
        for job in win32print.EnumJobs(handle, 0, -1, 1):
            doc = job.get('pDocument', '')
            status = job.get('Status', 0)
            if doc != 'Labelmate' and not (status & stuck_flags):
                continue
            job_id = job['JobId']
            for control in (win32print.JOB_CONTROL_CANCEL, win32print.JOB_CONTROL_DELETE):
                try:
                    win32print.SetJob(handle, job_id, 0, None, control)
                except win32print.error:
                    pass
            cleared += 1
    finally:
        win32print.ClosePrinter(handle)
    return cleared


def send_raw(printer_name: str, data: bytes) -> None:
    _require_windows()
    import win32print

    if uses_ipp_driver(printer_name):
        raise RuntimeError(
            f'"{printer_name}" uses {get_printer_driver(printer_name)}.\n\n{BROTHER_DRIVER_HELP}'
        )

    clear_stuck_jobs(printer_name)

    handle = win32print.OpenPrinter(printer_name)
    if not handle:
        raise RuntimeError(f'Could not open printer "{printer_name}".')

    try:
        win32print.StartDocPrinter(handle, 1, ('Labelmate', None, 'RAW'))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


def print_label(
    brand: str,
    model: str,
    size: str,
    printer_name: str = '',
    *,
    ql_model: str = 'QL-820NWB',
    label_size: str = '62',
) -> str:
    _require_windows()

    roll = LABEL_ROLLS.get(label_size, LABEL_ROLLS['62'])
    resolved = resolve_printer_name(printer_name)

    image = render_label(brand, model, size, label_size=label_size)
    data = build_raster_data(
        image,
        ql_model=ql_model,
        label_size=label_size,
        red=roll['red'],
    )
    send_raw(resolved, data)
    return resolved
