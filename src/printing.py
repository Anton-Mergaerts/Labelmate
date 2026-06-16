"""Render labels and print silently via the Brother Windows driver (RAW)."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.paths import logo_path

PRINTABLE_WIDTH_PX = 696
TAPE_WIDTH_PX = 732
DEFAULT_LABEL_HEIGHT_PX = 220
MARGIN = 10
LINE_GAP = 10
DIVIDER_GAP = 8
RIGHT_COLUMN_MIN_PX = 190
COLUMN_GAP = 20
LOGO_COLUMN_PX = 90
LOGO_GAP = 14
LABEL_HEADER_BANNER_TEXT = 'Printed using Labelmate® - Anton Mergaerts'
LABEL_FOOTER_BANNER_TEXT = 'www.kick.be - Go bother Cyriel'
BANNER_PAD_BOTTOM_PX = 2
BANNER_GAP_ABOVE_BODY_PX = 4
BODY_TIGHT_PAD_Y_PX = 2

FOOTER_SPACINGS = {
    'tight': {'name': 'Tight', 'gap_px': 3},
    'normal': {'name': 'Normal', 'gap_px': 6},
    'loose': {'name': 'Loose', 'gap_px': 10},
}

# Approximate extra tape feed the Brother driver adds beyond the raster (preview only).
PREVIEW_FEED_TOP_RATIO = 0.09
PREVIEW_FEED_BOTTOM_RATIO = 0.09

LABEL_ROLLS = {
    '62red': {'name': '62 mm black/red endless (demo roll)', 'red': True},
    '62': {'name': '62 mm black/white endless (DK-44205 paper)', 'red': False},
    '62x100': {'name': '62 mm x 100 mm die-cut', 'red': False},
    '62x29': {'name': '62 mm x 29 mm die-cut', 'red': False},
}

TEXT_SCALES = {
    'small': {'name': 'Small', 'factor': 0.82},
    'normal': {'name': 'Normal', 'factor': 1.0},
    'large': {'name': 'Large', 'factor': 1.2},
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


def text_scale_factor(text_scale: str) -> float:
    return TEXT_SCALES.get(text_scale, TEXT_SCALES['normal'])['factor']


def footer_spacing_gap(footer_spacing: str) -> int:
    return FOOTER_SPACINGS.get(footer_spacing, FOOTER_SPACINGS['normal'])['gap_px']


def _scaled(value: int, factor: float) -> int:
    return max(1, int(round(value * factor)))


def _trim_vertical_whitespace(image: Image.Image, pad: int) -> Image.Image:
    rgb = image.convert('RGB')
    pixels = rgb.load()
    width, height = rgb.size
    top = height
    bottom = -1
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != (255, 255, 255):
                top = min(top, y)
                bottom = max(bottom, y)
    if bottom < top:
        return image
    top = max(0, top - pad)
    bottom = min(height - 1, bottom + pad)
    return rgb.crop((0, top, width, bottom + 1))


def _label_logo_source() -> Image.Image | None:
    path = logo_path()
    if not path.exists():
        return None
    with Image.open(path) as loaded:
        return loaded.convert('RGBA')


def _logo_column(layout: str, factor: float, has_logo: bool) -> tuple[int, int]:
    if not has_logo:
        return 0, 0
    if layout == 'compact':
        return _scaled(48, factor), _scaled(6, factor)
    return _scaled(LOGO_COLUMN_PX, factor), _scaled(LOGO_GAP, factor)


def _fit_logo(logo: Image.Image, *, max_width: int, max_height: int) -> Image.Image:
    if logo.width <= max_width and logo.height <= max_height:
        return logo
    ratio = logo.width / logo.height
    height = min(max_height, int(round(max_width / ratio)))
    width = int(round(height * ratio))
    if width > max_width:
        width = max_width
        height = int(round(width / ratio))
    return logo.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)


def _paste_logo(base: Image.Image, logo: Image.Image, x: int, y: int) -> None:
    if logo.mode != 'RGBA':
        base.paste(logo, (x, y))
        return
    layer = Image.new('RGBA', base.size, (255, 255, 255, 0))
    layer.paste(logo, (x, y), logo)
    base.paste(layer, (0, 0), layer)


def _label_uses_banners(label_size: str) -> bool:
    return label_size in ('62', '62red')


def _banner_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    layout: str,
    factor: float,
):
    return _fit_font(
        draw,
        text,
        max_width=PRINTABLE_WIDTH_PX - _scaled(24, factor),
        start_size=_scaled(18 if layout == 'compact' else 22, factor),
        min_size=_scaled(13 if layout == 'compact' else 16, factor),
        bold=True,
    )


def _banner_layout(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    layout: str,
    factor: float,
) -> tuple[object, int, int, int]:
    font = _banner_font(draw, text, layout=layout, factor=factor)
    pad_bottom = _scaled(BANNER_PAD_BOTTOM_PX, factor)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    block_h = text_h + pad_bottom
    draw_y_offset = -bbox[1]
    return font, block_h, text_w, draw_y_offset


def _draw_banner_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    *,
    y_block: int,
    text_w: int,
    draw_y_offset: int,
) -> None:
    draw.text(
        ((PRINTABLE_WIDTH_PX - text_w) // 2, y_block + draw_y_offset),
        text,
        fill='#2a3038',
        font=font,
    )


def _compose_label_with_banners(
    body: Image.Image,
    *,
    layout: str,
    factor: float,
    footer_spacing: str = 'normal',
) -> Image.Image:
    probe = Image.new('RGB', (PRINTABLE_WIDTH_PX, 1), 'white')
    probe_draw = ImageDraw.Draw(probe)
    header_font, header_block, header_w, header_y_offset = _banner_layout(
        probe_draw,
        LABEL_HEADER_BANNER_TEXT,
        layout=layout,
        factor=factor,
    )
    footer_font, footer_block, footer_w, footer_y_offset = _banner_layout(
        probe_draw,
        LABEL_FOOTER_BANNER_TEXT,
        layout=layout,
        factor=factor,
    )
    gap_above = _scaled(BANNER_GAP_ABOVE_BODY_PX, factor)
    gap_below = _scaled(footer_spacing_gap(footer_spacing), factor)

    total_h = header_block + gap_above + body.height + gap_below + footer_block
    image = Image.new('RGB', (PRINTABLE_WIDTH_PX, total_h), 'white')
    draw = ImageDraw.Draw(image)

    _draw_banner_text(
        draw,
        LABEL_HEADER_BANNER_TEXT,
        header_font,
        y_block=0,
        text_w=header_w,
        draw_y_offset=header_y_offset,
    )

    body_y = header_block + gap_above
    image.paste(body, (0, body_y))

    _draw_banner_text(
        draw,
        LABEL_FOOTER_BANNER_TEXT,
        footer_font,
        y_block=body_y + body.height + gap_below,
        text_w=footer_w,
        draw_y_offset=footer_y_offset,
    )
    return image


def _render_label_body(
    brand: str,
    model: str,
    size: str,
    label_size: str,
    *,
    text_scale: str,
    show_logo: bool,
    tight_vertical: bool = False,
) -> Image.Image:
    factor = text_scale_factor(text_scale)
    height, layout = _label_height(label_size)
    if layout == 'large' and label_size not in ('62x100', '62x29') and not tight_vertical:
        height = _scaled(height, factor)

    margin = _scaled(6 if tight_vertical else (8 if layout == 'compact' else MARGIN), factor)
    line_gap = _scaled(4 if layout == 'compact' else LINE_GAP, factor)
    divider_gap = _scaled(4 if tight_vertical else (5 if layout == 'compact' else DIVIDER_GAP), factor)
    right_min = _scaled(88 if layout == 'compact' else RIGHT_COLUMN_MIN_PX, factor)
    column_gap = _scaled(10 if layout == 'compact' else COLUMN_GAP, factor)
    logo_source = _label_logo_source() if show_logo else None
    logo_column, logo_gap = _logo_column(layout, factor, logo_source is not None)
    text_left = margin + logo_column + logo_gap
    text_width = PRINTABLE_WIDTH_PX - text_left - margin

    image = Image.new('RGB', (PRINTABLE_WIDTH_PX, height), 'white')
    draw = ImageDraw.Draw(image)

    if layout == 'compact':
        size_font = _fit_font(
            draw,
            size,
            max_width=right_min,
            start_size=_scaled(34, factor),
            min_size=_scaled(22, factor),
            bold=True,
        )
        brand_font = _fit_font(
            draw,
            brand,
            max_width=text_width - right_min - column_gap,
            start_size=_scaled(24, factor),
            min_size=_scaled(16, factor),
            bold=True,
        )
        model_font = _fit_font(
            draw,
            model,
            max_width=text_width,
            start_size=_scaled(18, factor),
            min_size=_scaled(14, factor),
        )
    else:
        size_font = _fit_font(
            draw,
            size,
            max_width=right_min,
            start_size=_scaled(64, factor),
            min_size=_scaled(40, factor),
            bold=True,
        )
        brand_font = _fit_font(
            draw,
            brand,
            max_width=text_width - right_min - column_gap,
            start_size=_scaled(56, factor),
            min_size=_scaled(32, factor),
            bold=True,
        )
        model_font = _fit_font(
            draw,
            model,
            max_width=text_width,
            start_size=_scaled(38, factor),
            min_size=_scaled(24, factor),
        )

    size_w, size_h = _text_size(draw, size, size_font)
    _, brand_h = _text_size(draw, brand, brand_font)
    _, model_h = _text_size(draw, model, model_font)

    header_h = max(brand_h, size_h)
    model_gap = _scaled(6 if tight_vertical else 8, factor)
    block_h = header_h + divider_gap + 1 + model_gap + model_h
    y = margin if tight_vertical else max(margin, (height - block_h) // 2)

    size_x = PRINTABLE_WIDTH_PX - margin - size_w
    brand_y = y + (header_h - brand_h) // 2
    size_y = y + (header_h - size_h) // 2

    draw.text((text_left, brand_y), brand, fill='black', font=brand_font)
    draw.text((size_x, size_y), size, fill='black', font=size_font)

    rule_y = y + header_h + divider_gap
    draw.line((text_left, rule_y, PRINTABLE_WIDTH_PX - margin, rule_y), fill='#c8d0dc', width=1)

    model_y = rule_y + model_gap
    draw.text((text_left, model_y), model, fill='black', font=model_font)

    if logo_source is not None:
        logo = _fit_logo(
            logo_source,
            max_width=logo_column,
            max_height=max(1, height - margin * 2),
        )
        logo_x = margin + (logo_column - logo.width) // 2
        logo_y = y + (block_h - logo.height) // 2
        _paste_logo(image, logo, logo_x, logo_y)

    if tight_vertical:
        image = _trim_vertical_whitespace(image, _scaled(BODY_TIGHT_PAD_Y_PX, factor))

    return image


def render_label(
    brand: str,
    model: str,
    size: str,
    label_size: str = '62',
    *,
    text_scale: str = 'large',
    show_logo: bool = True,
    footer_spacing: str = 'normal',
) -> Image.Image:
    with_banners = _label_uses_banners(label_size)
    body = _render_label_body(
        brand,
        model,
        size,
        label_size,
        text_scale=text_scale,
        show_logo=show_logo,
        tight_vertical=with_banners,
    )
    if not with_banners:
        return body

    factor = text_scale_factor(text_scale)
    _, layout = _label_height(label_size)
    return _compose_label_with_banners(
        body,
        layout=layout,
        factor=factor,
        footer_spacing=footer_spacing,
    )


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


def _spooler_active_flags():
    import win32print

    return (
        win32print.JOB_STATUS_SPOOLING
        | win32print.JOB_STATUS_PRINTING
        | win32print.JOB_STATUS_RESTART
        | win32print.JOB_STATUS_PAUSED
    )


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
    active_flags = _spooler_active_flags()
    cleared = 0
    handle = win32print.OpenPrinter(printer_name)
    if not handle:
        return 0
    try:
        for job in win32print.EnumJobs(handle, 0, -1, 1):
            status = job.get('Status', 0)
            if status & active_flags:
                continue
            if not (status & stuck_flags):
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


def wait_for_spooler(printer_name: str, *, timeout: float = 180.0, poll: float = 0.3) -> None:
    """Wait until the printer has no active spooler jobs."""
    _require_windows()
    import time
    import win32print

    active_flags = _spooler_active_flags()
    deadline = time.time() + timeout
    while time.time() < deadline:
        handle = win32print.OpenPrinter(printer_name)
        if not handle:
            raise RuntimeError(f'Could not open printer "{printer_name}".')
        try:
            busy = any(
                job.get('Status', 0) & active_flags
                for job in win32print.EnumJobs(handle, 0, -1, 1)
            )
            if not busy:
                return
        finally:
            win32print.ClosePrinter(handle)
        time.sleep(poll)
    raise RuntimeError('Timed out waiting for the printer queue to finish.')


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
    text_scale: str = 'large',
    show_logo: bool = True,
    footer_spacing: str = 'normal',
    wait_for_queue: bool = False,
) -> str:
    _require_windows()

    roll = LABEL_ROLLS.get(label_size, LABEL_ROLLS['62'])
    resolved = resolve_printer_name(printer_name)

    image = render_label(
        brand,
        model,
        size,
        label_size=label_size,
        text_scale=text_scale,
        show_logo=show_logo,
        footer_spacing=footer_spacing,
    )
    data = build_raster_data(
        image,
        ql_model=ql_model,
        label_size=label_size,
        red=roll['red'],
    )
    send_raw(resolved, data)
    if wait_for_queue:
        wait_for_spooler(resolved)
    return resolved
