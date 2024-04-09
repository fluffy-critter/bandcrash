# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('camptown')

import bandcrash.__version__
import sys

a = Analysis(
    ['bandcrash-gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='bandcrash-gui',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch='universal2',
        codesign_identity=None,
        entitlements_file=None,
        icon='art/bclogo.png',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='bandcrash-gui',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
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
    name='bandcrash',
    icon='bclogo.png',
)
app = BUNDLE(
    coll,
    name='Bandcrash.app',
    icon='art/bclogo.png',
    version=bandcrash.__version__,
    bundle_identifier='biz.beesbuzz.bandcrash',
    info_plist={
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Bandcrash Album',
            'CFBundleTypeExtensions': ['bcalbum', 'json', ],
            'CFBundleTypeRole': "Viewer",
        }],
    }
)
