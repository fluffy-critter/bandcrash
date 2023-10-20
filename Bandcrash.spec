# -*- mode: python ; coding: utf-8 -*-

import bandcrash.__version__
import sys

a = Analysis(
    ['bandcrash-gui.py'],
    pathex=[],
    binaries=[],
    datas=[('bandcrash/jinja_templates/*', 'bandcrash/jinja_templates')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bandcrash',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='universal2' if sys.platform == 'darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
    icon='art/bclogo.png',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Bandcrash',
    icon='bclogo.png',
)
app = BUNDLE(
    coll,
    name='Bandcrash.app',
    icon='art/bclogo.png',
    version=bandcrash.__version__.__version__,
    bundle_identifier='biz.beesbuzz.bandcrash',
    info_plist={
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Bandcrash Album',
            'CFBundleTypeExtensions': ['bcalbum', 'json', ],
            'CFBundleTypeRole': "Viewer",
        }],
    }
)
