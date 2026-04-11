# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('info_main.txt', '.'), ('info_viewer.txt', '.'), ('drawer.ico', '.'), ('fonts', 'fonts')],
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
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='drawer_0_2_0',
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
