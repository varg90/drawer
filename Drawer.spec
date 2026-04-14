# -*- mode: python ; coding: utf-8 -*-
#
# Drawer build spec. Used by local builds and GitHub Actions CI on both
# Windows and macOS.
#
# Build mode:
#   macOS: always produces a Drawer.app bundle (onedir + BUNDLE)
#   Windows: controlled by DRAWER_BUILD_MODE env var
#     - "onefile" (default): single portable Drawer.exe
#     - "onedir":            folder used as source for the Inno Setup installer
#
# Size optimizations applied on both platforms:
#   - Drop opengl32sw (Windows software OpenGL fallback, ~5 MB)
#   - Drop Qt Pdf/Network/OpenGL/Svg binaries (modules already excluded,
#     but PyInstaller still copies the DLLs/frameworks)
#   - Drop all Qt translations except *_en.qm

import os
import sys

IS_MACOS = sys.platform == 'darwin'
WINDOWS_ONEFILE = not IS_MACOS and os.environ.get("DRAWER_BUILD_MODE", "onefile") == "onefile"

# Substrings matched against binary destination paths.
# Windows dll names and macOS framework paths are both covered:
#   Windows: PyQt6\Qt6\bin\Qt6Pdf.dll
#   macOS:   PyQt6/Qt6/lib/QtPdf.framework/Versions/A/QtPdf
# Exact filenames we drop from the bundle. Substring matching is too loose:
# e.g. "Qt6OpenGL" would also match "Qt6OpenGLWidgets.dll", which is needed
# at runtime by PyQt6 and whose absence surfaces as a generic
# "Failed to load Python DLL python3XX.dll" at launch (PyInstaller reports
# early-bootstrap failures with that message).
DROP_BINARY_BASENAMES = frozenset((
    # Windows DLLs
    "opengl32sw.dll",
    "Qt6Pdf.dll",
    "Qt6Network.dll",
    "Qt6OpenGL.dll",
    "Qt6Svg.dll",
    # macOS frameworks — PyInstaller copies the inner binary as well as
    # framework-internal Resources/Info.plist etc.; matching on the plain
    # binary name inside the framework is sufficient, since every entry
    # for a given framework has the framework name as a path segment.
))

# macOS path-segment matches (framework directories we drop entirely).
DROP_FRAMEWORK_DIRS = frozenset((
    "QtPdf.framework",
    "QtNetwork.framework",
    "QtOpenGL.framework",
    "QtSvg.framework",
))

# UPX corrupts some Windows runtime DLLs — never compress these.
# python3*.dll is the critical one.
UPX_EXCLUDES = [
    "python3*.dll",
    "vcruntime*.dll",
    "msvcp*.dll",
    "msvcr*.dll",
    "api-ms-win-*.dll",
    "ucrtbase.dll",
]

def _keep_binary(entry):
    dest = entry[0].replace("\\", "/")
    basename = dest.rsplit("/", 1)[-1]
    if basename in DROP_BINARY_BASENAMES:
        return False
    for fw in DROP_FRAMEWORK_DIRS:
        if f"/{fw}/" in dest or dest.startswith(f"{fw}/"):
            return False
    return True

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
    optimize=2,  # strips docstrings + asserts
)

# PyInstaller has no flag to exclude binaries by path, so post-filter the
# Analysis TOC in place. This is the idiomatic workaround.
a.binaries = [b for b in a.binaries if _keep_binary(b)]
a.datas = [d for d in a.datas if _keep_data(d)]

pyz = PYZ(a.pure)

if IS_MACOS:
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
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=UPX_EXCLUDES,
        name='Drawer',
    )
    app = BUNDLE(
        coll,
        name='Drawer.app',
        icon='drawer.icns',
        bundle_identifier='com.drawer.app',
    )
elif WINDOWS_ONEFILE:
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
        upx_exclude=UPX_EXCLUDES,
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
        upx_exclude=UPX_EXCLUDES,
        name='Drawer',
    )
