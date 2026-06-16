"""Printer setup links and Windows shortcuts for Labelmate."""

from __future__ import annotations

import subprocess
import sys
import webbrowser

# Brother QL-820NWB driver downloads (user picks OS on the page).
BROTHER_QL820_DOWNLOAD_URL = (
    'https://support.brother.com/g/b/downloadlist.aspx?prod=lpql820nwbeuk'
)

SETUP_CHECKLIST = (
    '1. Install the official Brother QL-820NWB driver from brother.com '
    '(not the Microsoft IPP Class Driver).\n'
    '2. Connect the printer via USB and add it in Windows. Editor Lite must be OFF.\n'
    '3. In Labelmate → Printer Settings → choose your Brother printer and label roll '
    '(DK-44205 = 62 mm black/white endless).'
)

TROUBLESHOOTING_INFO = (
    'You usually do not need to change these — only if something goes wrong:\n'
    '• Communication popups (“Communicatiefout”) → Printer properties → Ports → '
    'turn OFF “Enable bidirectional support”.\n'
    '• Blank or garbled labels → Printer Setting Tool → Device Settings → '
    'Command Mode: Raster (not P-touch Template). Then power-cycle the printer.\n'
    '• Labelmate switches to Raster mode automatically on each print.'
)

IPP_DRIVER_FIX_STEPS = (
    'The Microsoft IPP driver cannot print Labelmate labels. Fix it this way:\n'
    '1. Windows Settings → Printers → remove the Brother QL printer.\n'
    '2. Download and run the official Brother QL-820NWB driver installer (button below).\n'
    '3. Plug in USB when the installer asks and finish setup.\n'
    '4. Confirm the driver is “Brother QL-820NWB”, not “Microsoft IPP Class Driver”.\n'
    '5. If you still see communication popups, try Printer properties → Ports → '
    'disable bidirectional support (optional — many setups work without this).'
)


def open_brother_driver_download() -> None:
    webbrowser.open(BROTHER_QL820_DOWNLOAD_URL)


def open_windows_printers() -> None:
    if sys.platform != 'win32':
        return
    subprocess.Popen(['explorer.exe', 'ms-settings:printers'], shell=False)


def open_printer_properties(printer_name: str) -> None:
    if sys.platform != 'win32' or not printer_name.strip():
        open_windows_printers()
        return
    subprocess.Popen(
        [
            'rundll32',
            'printui.dll,PrintUIEntry',
            '/p',
            '/n',
            printer_name.strip(),
        ],
        shell=False,
    )
