#!/usr/bin/env python3
"""
Genere icon.ico (Windows) et icon.icns (macOS) depuis icon_source.png.
Usage : python make_icon.py
"""
import sys, os, subprocess, shutil

try:
    from PIL import Image
except ImportError:
    print("Pillow requis : pip install pillow")
    sys.exit(1)

SOURCE = "icon_source.png"


def load_source() -> Image.Image:
    if not os.path.exists(SOURCE):
        print(f"[ERREUR] {SOURCE} introuvable — placez l'image source dans le dossier du projet.")
        sys.exit(1)
    img = Image.open(SOURCE).convert("RGBA")
    # Recadrage carre si necessaire
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img  = img.crop((left, top, left + side, top + side))
    return img


def save_ico(path: str) -> None:
    src    = load_source()
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    images = [src.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]
    images[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"[OK] {path}")


def save_icns(path: str) -> None:
    if sys.platform != "darwin":
        print("  (icon.icns skipped - macOS only)")
        return
    src     = load_source()
    iconset = path.replace(".icns", ".iconset")
    os.makedirs(iconset, exist_ok=True)
    spec = {
        "icon_16x16":      16,
        "icon_16x16@2x":   32,
        "icon_32x32":      32,
        "icon_32x32@2x":   64,
        "icon_128x128":    128,
        "icon_128x128@2x": 256,
        "icon_256x256":    256,
        "icon_256x256@2x": 512,
        "icon_512x512":    512,
        "icon_512x512@2x": 1024,
    }
    for name, size in spec.items():
        src.resize((size, size), Image.Resampling.LANCZOS).save(
            os.path.join(iconset, f"{name}.png")
        )
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", path], check=True)
    shutil.rmtree(iconset)
    print(f"[OK] {path}")


if __name__ == "__main__":
    save_ico("icon.ico")
    save_icns("icon.icns")
