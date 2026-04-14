# -*- mode: python ; coding: utf-8 -*-
#
# Drawer build spec. Used by both local builds and GitHub Actions CI.
#
# Build mode is controlled by DRAWER_BUILD_MODE env var:
#   - "onefile" (default): single portable Drawer.exe
#   - "onedir": folder layout used as source for the Inno Setup installer
#
# Size optimizations applied to both modes:
#   - Drop opengl32sw.dll (software OpenGL fallback, ~5 MB compressed, unused)
#   - Drop Qt6Pdf/Network/OpenGL/Svg DLLs (modules excluded but DLLs otherwise shipped)
#   - Drop all Qt translations except English

import os

ONEFILE = os.environ.get("DRAWER_BUILD_MODE", "onefile") == "onefile"

DROP_BINARIES_SUBSTRINGS = (
    "opengl32sw",
    "Qt6Pdf",
    "Qt6Network",
    "Qt6OpenGL",
    "Qt6Svg",
)

def _keep_binary(entry):
    dest = entry[0].replace("\\", "/")
    return not any(s in dest for s in DROP_BINARIES_SUBSTRINGS)

def _keep_data(entry):
    dest = entry[0].replace("\\", "/")
    if "translations/" in dest and dest.endswith(".qm"):
        return dest.endswith("_en.qm")
    return True


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('info_main.txt', '.'),
        ('info_viewer.txt', '.'),
        ('drawer.ico', '.'),
        ('fonts', 'fonts'),
        ('Cat', 'Cat'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtNetwork', 'PyQt6.QtQml', 'PyQt6.QtQuick',
        'PyQt6.QtWebEngine', 'PyQt6.QtMultimedia', 'PyQt6.QtSvg',
        'PyQt6.QtOpenGL', 'PyQt6.QtDBus', 'PyQt6.QtSql',
        'PyQt6.QtPdf', 'PyQt6.QtBluetooth', 'PyQt6.QtSerialPort',
        'PyQt6.QtDesigner', 'PyQt6.QtHelp', 'PyQt6.QtTest',
        'PIL', 'unittest', 'test', 'sqlite3',
    ],
    noarchive=False,
    optimize=2,
)

a.binaries = [b for b in a.binaries if _keep_binary(b)]
a.datas = [d for d in a.datas if _keep_data(d)]

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='Drawer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='drawer.ico',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Drawer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='drawer.ico',
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='Drawer',
    )
