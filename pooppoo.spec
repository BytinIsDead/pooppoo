# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for pooppoo browser
# Builds single-file executable for GitHub runner
block_cipher = None

a = Analysis(
    ['src/pooppoo/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'gi', 'gi.repository.Gtk', 'gi.repository.WebKit2', 'gi.repository.GLib', 'gi.repository.Gio',
        'cairo', 'bs4', 'requests'
    ],
    hookspath=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pooppoo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico' if __import__('os').path.exists('assets/icon.ico') else None,
)
