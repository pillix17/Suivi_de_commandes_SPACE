# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — macOS
# Build : pyinstaller build_macos.spec

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("templates",              "templates"),
        ("produits_reference.csv", "."),
    ],
    hiddenimports=[
        "flask", "jinja2", "jinja2.ext", "markupsafe", "werkzeug",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",
        "pandas._libs.tslibs.timezones",
        "pandas._libs.sparse",
        "pandas._libs.ops",
        "pandas._libs.hashtable",
        "pandas._libs.lib",
        "encodings.utf_8_sig",
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
    [],
    exclude_binaries=True,
    name="SuiviCommandes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    argv_emulation=True,      # Nécessaire pour .app macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SuiviCommandes",
)

app_bundle = BUNDLE(
    coll,
    name="SuiviCommandes.app",
    icon="icon.icns",
    bundle_identifier="com.paulmolusson.suivicommandes",
    info_plist={
        "CFBundleName":               "Suivi Commandes SPACE",
        "CFBundleDisplayName":        "Suivi Commandes SPACE",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion":            "1.0.0",
        "NSHighResolutionCapable":    True,
        "LSMinimumSystemVersion":     "11.0",
        "NSHumanReadableCopyright":   "© 2026 Paul Molusson",
    },
)
