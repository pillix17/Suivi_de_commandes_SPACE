#!/usr/bin/env python3
"""
Génère icon.ico (Windows) et icon.icns (macOS) depuis Pillow.
Usage : python make_icon.py
"""
import sys, os, subprocess, shutil, tempfile

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow requis : pip install pillow")
    sys.exit(1)


def draw_icon(size: int) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r    = size // 5                          # rayon des coins

    # Fond arrondi — bleu nuit
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(15, 23, 42))

    pad  = size // 7
    x0, y0, x1, y1 = pad, pad, size - pad, size - pad
    hdr  = (y1 - y0) // 4                    # hauteur de l'en-tête
    lw   = max(1, size // 64)
    tw   = x1 - x0

    # En-tête bleue
    draw.rectangle([x0, y0, x1, y0 + hdr], fill=(30, 58, 138))

    # Bordures du tableau
    draw.rectangle([x0, y0, x1, y1], outline=(71, 85, 105), width=lw)

    # Séparateur en-tête
    draw.line([x0, y0 + hdr, x1, y0 + hdr], fill=(71, 85, 105), width=lw)

    # Lignes de lignes (3 lignes)
    body_h = y1 - (y0 + hdr)
    for i in (1, 2):
        ry = y0 + hdr + body_h * i // 3
        draw.line([x0, ry, x1, ry], fill=(51, 65, 85), width=max(1, lw - 1))

    # Séparateurs de colonnes (40 % et 70 %)
    for frac in (0.40, 0.70):
        cx = x0 + int(tw * frac)
        draw.line([cx, y0, cx, y1], fill=(51, 65, 85), width=max(1, lw - 1))

    # Points colorés dans l'en-tête (rouge / vert / bleu)
    dot_y = y0 + hdr // 2
    dot_r = max(2, size // 28)
    for frac, color in zip(
        (0.20, 0.55, 0.85),
        ((96, 165, 250), (167, 243, 208), (252, 211, 77)),
    ):
        cx = x0 + int(tw * frac)
        draw.ellipse(
            [cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r],
            fill=color,
        )

    return img


def save_ico(path: str) -> None:
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]
    images[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"✓ {path}")


def save_icns(path: str) -> None:
    if sys.platform != "darwin":
        print("  (icon.icns ignoré — macOS seulement)")
        return
    iconset = path.replace(".icns", ".iconset")
    os.makedirs(iconset, exist_ok=True)
    spec = {
        "icon_16x16": 16,    "icon_16x16@2x": 32,
        "icon_32x32": 32,    "icon_32x32@2x": 64,
        "icon_128x128": 128, "icon_128x128@2x": 256,
        "icon_256x256": 256, "icon_256x256@2x": 512,
        "icon_512x512": 512, "icon_512x512@2x": 1024,
    }
    for name, size in spec.items():
        draw_icon(size).save(os.path.join(iconset, f"{name}.png"))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", path], check=True)
    shutil.rmtree(iconset)
    print(f"✓ {path}")


if __name__ == "__main__":
    save_ico("icon.ico")
    save_icns("icon.icns")
