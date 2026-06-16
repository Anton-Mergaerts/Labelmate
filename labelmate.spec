# PyInstaller build spec for Labelmate (Windows).
# Build:  build_exe.bat

from PyInstaller.utils.hooks import collect_all

block_cipher = None

brother_datas, brother_binaries, brother_hidden = collect_all('brother_ql')

asset_datas = [('assets', 'assets')]

a = Analysis(
    ['labelmate.py'],
    pathex=[],
    binaries=brother_binaries,
    datas=brother_datas + asset_datas,
    hiddenimports=[
        'win32print',
        'win32api',
        'pywintypes',
        'brother_ql.conversion',
        'brother_ql.raster',
        'brother_ql.backends.helpers',
        'brother_ql.backends',
        'brother_ql.devicedependent',
        *brother_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Labelmate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Labelmate',
)
