# Labelmate

Desktop app for printing product labels on a **Brother QL-820NWB** (62 mm tape). Pick brand, model, and size from a catalog, preview the label, and print silently via the Windows Brother driver.

**Current status:** early preview (`0.0.x`) — working prints on QL-820NWB, but still evolving.

## Download (recommended for most users)

You do **not** need Python installed.

1. Open **[Releases](https://github.com/Anton-Mergaerts/Labelmate/releases)** on GitHub.
2. Download **`Labelmate-windows.zip`** from the latest release.
3. Extract the zip to a folder (e.g. `C:\Labelmate`).
4. Run **`Labelmate.exe`**.

### Before first print

On the PC that will print:

1. Install the official **Brother QL-820NWB** driver from [brother.com](https://www.brother.com).
2. Add the printer in **Windows Settings → Printers**.
3. In the printer’s **Printer properties → Ports**, turn **off** “Enable bidirectional support” (helps avoid communication popups).
4. On the printer: **Editor Lite** light must be **off**.
5. In Labelmate: **Printer Settings** → choose your Brother printer and the correct roll (DK-44205 = **62 mm black/white endless**).

The app stores its data in `%APPDATA%\Labelmate` (catalog database, printer settings, backups).

## System Check

Labelmate runs a **System Check** on startup and has a **System Check** button in the main window. Use it if printing is blocked or the Brother driver is wrong (e.g. Microsoft IPP driver).

## Build from source (developers)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python labelmate.py
```

### Build the Windows executable

```bat
build_exe.bat
```

Output: `dist\Labelmate\` — zip this folder for a GitHub Release (see `RELEASE.md`).

Dev data paths:

- Catalog database: `data\labelmate.db`
- Printer settings: `app_data\settings\printer_settings.json`

## Publishing a new version

See **[RELEASE.md](RELEASE.md)** for tagging and uploading builds to GitHub Releases.

## License

Add your license here if you plan to share the project publicly.
