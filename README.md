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
3. On the printer: **Editor Lite** light must be **off**.
4. In Labelmate: **Printer Settings** → choose your Brother printer and the correct roll (DK-44205 = **62 mm black/white endless**).

**If something goes wrong:** communication popups may be fixed by turning off bidirectional support (Printer properties → Ports). Blank labels may need Raster mode in Brother’s Printer Setting Tool. See **Printer Setup** in the app for details.

The app stores its data in `%APPDATA%\Labelmate` (catalog database, printer settings, backups).

## Printer Setup

Use **Settings → Printer Setup** in the menu bar for a first-time checklist, links to the official Brother driver download, Windows printer settings, and a system check (driver, printer, roll type).

Labelmate cannot install Brother drivers for you — download them from Brother’s site using the button in Printer Setup.

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

- Catalog database: `data\labelmate.db` (or `%APPDATA%\Labelmate\data\labelmate.db` for the exe)
- Printer settings: `app_data\settings\printer_settings.json`
- CSV: **Settings → Database Manager → Tools** — export/import `brand,model,size` rows

## Publishing a new version

See **[RELEASE.md](RELEASE.md)** for tagging and uploading builds to GitHub Releases.

## License

Add your license here if you plan to share the project publicly.
