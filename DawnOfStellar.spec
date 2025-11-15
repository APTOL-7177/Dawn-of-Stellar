# -*- mode: python ; coding: utf-8 -*-
# Dawn of Stellar - PyInstaller Spec File

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all tcod data files
tcod_datas = collect_data_files('tcod')

# Collect all hidden imports
hiddenimports = collect_submodules('tcod')
hiddenimports += ['yaml', 'numpy', 'numpy.core._methods', 'numpy.lib.format']

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data', 'data'),
        ('assets', 'assets'),
    ] + tcod_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'scipy',
        'pandas',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DawnOfStellar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # True for debugging, False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

# macOS app bundle
app = BUNDLE(
    exe,
    name='DawnOfStellar.app',
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    bundle_identifier='com.dawnofstellar.game',
)
