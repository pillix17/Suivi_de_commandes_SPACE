# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Windows
# Build : pyinstaller build_windows.spec

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("templates",             "templates"),
        ("produits_reference.csv", "."),
    ],
    hiddenimports=[
        # Waitress
        "waitress",
        "waitress.runner",
        "waitress.task",
        "waitress.channel",
        "waitress.server",
        # Flask / Jinja2
        "flask",
        "jinja2",
        "jinja2.ext",
        "markupsafe",
        "werkzeug",
        "werkzeug.routing",
        # Pandas internals souvent non-détectés
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",
        "pandas._libs.tslibs.timezones",
        "pandas._libs.sparse",
        "pandas._libs.ops",
        "pandas._libs.hashtable",
        "pandas._libs.lib",
        # Encodages
        "encodings.utf_8_sig",
        "encodings.cp1252",
        "encodings.latin_1",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "scipy", "IPython", "notebook",
        "tkinter", "test", "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SuiviCommandes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Pas de fenêtre console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
    version_file=None,
)
