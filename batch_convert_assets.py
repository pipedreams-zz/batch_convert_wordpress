#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Tuple, Dict, Optional

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Fehler: Pillow ist nicht installiert. Bitte mit `pip install Pillow` nachinstallieren.")
    sys.exit(1)

# Erhöhe das Decompression-Bomb-Limit für große Bilder (z.B. hochauflösende Scans)
# Standard: ~89 MP, Neu: ~300 MP (ausreichend für die meisten legitimen Fotos)
Image.MAX_IMAGE_PIXELS = 300_000_000

# Optional: AVIF-Support nachladen (falls installiert)
try:
    import pillow_avif  # noqa: F401
    AVIF_AVAILABLE = True
except Exception:
    AVIF_AVAILABLE = False

# PDF-Unterstützung via PyMuPDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False


# ------------------------------
# Utility: WordPress-freundliche Slug-Erstellung
# ------------------------------
UMLAUT_MAP = {
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "ae", "Ö": "oe", "Ü": "ue",
    "ß": "ss",
}

def wp_slugify(name: str) -> str:
    # Dateiendung entfernen, nur der Name
    base = name
    # Umlaute/ß ersetzen
    for k, v in UMLAUT_MAP.items():
        base = base.replace(k, v)
    # Unicode Normalisierung (Diakritika entfernen)
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    # Kleinbuchstaben
    base = base.lower()
    # Nicht alphanumerische Zeichen zu Bindestrichen
    base = re.sub(r"[^a-z0-9]+", "-", base)
    # Mehrfache Bindestriche reduzieren
    base = re.sub(r"-{2,}", "-", base)
    # Rand-Bindestriche abschneiden
    base = base.strip("-")
    # Fallback
    return base or "datei"

def normalize_prefix(prefix: str) -> str:
    """
    Normalisiert den Prefix: Kleinbuchstaben, nur alphanumerische Zeichen.
    Fügt automatisch einen Bindestrich am Ende hinzu, falls nicht vorhanden.
    """
    if not prefix:
        return ""
    # Kleinbuchstaben und nur alphanumerische Zeichen behalten
    normalized = re.sub(r"[^a-z0-9]+", "", prefix.lower())
    # Bindestrich am Ende hinzufügen
    if normalized and not normalized.endswith("-"):
        normalized += "-"
    return normalized

def ensure_prefix(slug: str, prefix: str) -> str:
    """
    Prüft, ob der Slug bereits mit dem Prefix beginnt.
    Falls nicht, wird der Prefix vorangestellt.
    """
    if not prefix:
        return slug
    # Prefix ohne Bindestrich für Vergleich
    prefix_base = prefix.rstrip("-")
    # Prüfen ob Slug bereits mit Prefix beginnt (mit oder ohne Bindestrich)
    if slug.startswith(prefix) or slug.startswith(prefix_base):
        return slug
    # Prefix hinzufügen
    return f"{prefix}{slug}"


# ------------------------------
# Konvertierung
# ------------------------------
SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
SUPPORTED_PDF_EXTS = {".pdf"}

def ask(prompt: str, default: Optional[str] = None) -> str:
    s = f"{prompt}"
    if default is not None:
        s += f" [{default}]"
    s += ": "
    val = input(s).strip()
    return val or (default if default is not None else "")

def parse_ext_list(s: str) -> Tuple[str, ...]:
    items = [x.strip().lower().lstrip(".") for x in s.split(",") if x.strip()]
    return tuple(f".{x}" for x in items)

def ensure_output_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def compute_new_size(img: Image.Image, target_width: int) -> Tuple[int, int]:
    w, h = img.size
    if w <= target_width:
        # keine Vergrößerung – Originalgröße behalten
        return w, h
    ratio = target_width / float(w)
    return target_width, max(1, int(round(h * ratio)))

def load_image_fix_orientation(path: Path) -> Image.Image:
    im = Image.open(path)
    try:
        im = ImageOps.exif_transpose(im)
    except Exception:
        pass
    return im

def pil_mode_for_format(im: Image.Image, fmt: str) -> Image.Image:
    # Für Web-Formate meist sRGB/RGB sinnvoll (kein CMYK)
    if fmt in {"jpg", "jpeg", "webp", "avif"}:
        if im.mode in ("RGBA", "LA", "P"):  # Transparenz -> auf Weiß setzen oder behalten?
            # Für JPG/WebP ohne Alpha -> auf Weiß flatten
            if fmt in {"jpg", "jpeg"}:
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
                return bg
            # Für WebP/AVIF mit Alpha darf RGBA bleiben
            if im.mode != "RGBA":
                return im.convert("RGBA")
            return im
        # CMYK/sonstiges -> RGB
        if im.mode not in ("RGB", "RGBA"):
            return im.convert("RGB")
        return im
    elif fmt == "png":
        # PNG kann Alpha, also RGBA bevorzugt
        if im.mode in ("P", "LA"):
            return im.convert("RGBA")
        if im.mode not in ("RGB", "RGBA"):
            return im.convert("RGBA" if "A" in im.getbands() else "RGB")
        return im
    return im

def save_image(im: Image.Image, out_path: Path, out_fmt: str, quality: int):
    out_fmt_upper = out_fmt.upper()
    params = {}
    if out_fmt_upper in {"JPG", "JPEG"}:
        params.update(dict(quality=quality, optimize=True, progressive=True, subsampling="4:2:0"))
        im = pil_mode_for_format(im, "jpg")
        im.save(out_path, format="JPEG", **params)
    elif out_fmt_upper == "PNG":
        # PNG "quality" nicht relevant; compress_level 0-9
        im = pil_mode_for_format(im, "png")
        params.update(dict(compress_level=6))
        im.save(out_path, format="PNG", **params)
    elif out_fmt_upper == "WEBP":
        im = pil_mode_for_format(im, "webp")
        params.update(dict(quality=quality, method=6))
        im.save(out_path, format="WEBP", **params)
    elif out_fmt_upper == "AVIF":
        if not AVIF_AVAILABLE:
            raise RuntimeError("AVIF wird nicht unterstützt (pillow-avif-plugin nicht installiert).")
        im = pil_mode_for_format(im, "avif")
        # pillow-avif-plugin nutzt 'quality'
        params.update(dict(quality=quality))
        im.save(out_path, format="AVIF", **params)
    else:
        raise ValueError(f"Unbekanntes Ausgabeformat: {out_fmt_upper}")

def page_suffix(idx: int) -> str:
    # -p001, -p002 ...
    return f"-p{idx:03d}"

def unique_target_path(base_dir: Path, base_name: str, ext: str, taken: Dict[str, int]) -> Path:
    """
    base_name ist bereits slugified und ohne Erweiterung.
    - Erstes Vorkommen: {base_name}{ext}
    - Kollisionen: {base_name}-001{ext}, -002, ...
    """
    candidate = f"{base_name}{ext}"
    if candidate not in taken:
        taken[candidate] = 0
        return base_dir / candidate
    # bereits vorhanden -> hochzählen
    taken[candidate] += 1
    num = taken[candidate]
    candidate2 = f"{base_name}-{num:03d}{ext}"
    # Sicherheit: falls auch das schon existiert (z. B. wegen Laufstart), schleife weiter
    while (base_dir / candidate2).exists():
        num += 1
        candidate2 = f"{base_name}-{num:03d}{ext}"
    # den Zähler für den Basisschlüssel merken
    taken[candidate] = num
    return base_dir / candidate2

def convert_image_file(
    src_path: Path,
    out_dir: Path,
    out_fmt: str,
    target_width: int,
    quality: int,
    taken: Dict[str, int],
    prefix: str = "",
):
    im = load_image_fix_orientation(src_path)
    w, h = compute_new_size(im, target_width)
    if (w, h) != im.size:
        im = im.resize((w, h), Image.LANCZOS)

    base_slug = wp_slugify(src_path.stem)
    base_slug = ensure_prefix(base_slug, prefix)
    ext = "." + out_fmt.lower().replace("jpeg", "jpg")
    out_path = unique_target_path(out_dir, base_slug, ext, taken)
    save_image(im, out_path, out_fmt, quality)
    print(f"OK: {src_path}  ->  {out_path}")

def convert_pdf_file(
    src_path: Path,
    out_dir: Path,
    out_fmt: str,
    target_width: int,
    quality: int,
    taken: Dict[str, int],
    pdf_zoom: float = 2.0,  # ~ 144 DPI (72 * 2)
    prefix: str = "",
):
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError(
            "PDF-Konvertierung benötigt PyMuPDF (pymupdf). Bitte mit `pip install pymupdf` installieren."
        )
    doc = fitz.open(src_path)
    base_slug = wp_slugify(src_path.stem)
    base_slug = ensure_prefix(base_slug, prefix)
    ext = "." + out_fmt.lower().replace("jpeg", "jpg")

    for i, page in enumerate(doc, start=1):
        # Rendern
        mat = fitz.Matrix(pdf_zoom, pdf_zoom)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        mode = "RGBA" if pix.alpha else "RGB"
        im = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        # Resize
        w, h = compute_new_size(im, target_width)
        if (w, h) != im.size:
            im = im.resize((w, h), Image.LANCZOS)

        # Seiten-Suffix an Basisslug anhängen, damit Multi-PDFs nachvollziehbar sind
        base_with_page = f"{base_slug}{page_suffix(i)}"
        candidate_key = f"{base_with_page}{ext}"
        if candidate_key not in taken:
            taken[candidate_key] = 0  # separat zählen je Seite
        out_path = unique_target_path(out_dir, base_with_page, ext, taken)
        save_image(im, out_path, out_fmt, quality)
        print(f"OK: {src_path} [Seite {i}]  ->  {out_path}")

    doc.close()


def walk_and_convert(
    in_dir: Path,
    out_dir: Path,
    include_exts: Iterable[str],
    out_fmt: str,
    target_width: int,
    quality: int,
    pdf_zoom: float,
    prefix: str = "",
):
    ensure_output_dir(out_dir)

    exts = tuple(e.lower() for e in include_exts)
    taken: Dict[str, int] = {}

    for src in in_dir.rglob("*"):
        if not src.is_file():
            continue
        ext = src.suffix.lower()
        if ext not in exts:
            continue

        try:
            if ext in SUPPORTED_PDF_EXTS:
                convert_pdf_file(
                    src, out_dir, out_fmt, target_width, quality, taken, pdf_zoom=pdf_zoom, prefix=prefix
                )
            elif ext in SUPPORTED_IMAGE_EXTS:
                convert_image_file(
                    src, out_dir, out_fmt, target_width, quality, taken, prefix=prefix
                )
            else:
                print(f"Übersprungen (nicht unterstützt): {src}")
        except Exception as e:
            print(f"FEHLER bei {src}: {e}")


def main():
    print("=== Batch-Konverter: TIF/JPG/PNG/PDF -> AVIF/WEBP/PNG/JPG (WordPress-optimierte Namen) ===\n")

    in_dir = Path(ask("Quellordner eingeben", ".")).expanduser().resolve()
    if not in_dir.exists() or not in_dir.is_dir():
        print(f"Fehler: Quellordner '{in_dir}' existiert nicht.")
        sys.exit(2)

    # Standard-Ausgabeverzeichnis ist ein Unterordner des Quellordners
    default_out_dir = in_dir / "output-web"
    out_dir_input = ask("Zielordner eingeben", str(default_out_dir))
    out_dir = Path(out_dir_input).expanduser().resolve()

    # Prefix abfragen (optional)
    prefix_input = ask("Dateinamen-Prefix (z.B. ABC123, optional - Enter für keinen)", "")
    prefix = normalize_prefix(prefix_input)
    if prefix_input and prefix:
        print(f"  → Normalisierter Prefix: '{prefix}'")
    elif prefix_input and not prefix:
        print("  → Warnung: Prefix enthält keine gültigen Zeichen und wird ignoriert.")

    include = ask("Dateimuster (Komma-getrennt), z.B. tif,jpg,png,pdf", "tif,jpg,jpeg,png,pdf")
    include_exts = parse_ext_list(include)

    out_fmt = ask("Zielformat (avif/webp/png/jpg)", "webp").lower()
    if out_fmt not in {"avif", "webp", "png", "jpg", "jpeg"}:
        print("Fehler: Ungültiges Zielformat.")
        sys.exit(3)
    if out_fmt == "jpeg":
        out_fmt = "jpg"
    if out_fmt == "avif" and not AVIF_AVAILABLE:
        print("Hinweis: AVIF-Support nicht gefunden. Installiere `pillow-avif-plugin`, oder wähle ein anderes Format.")
        proceed = ask("Trotzdem fortfahren (y/n)?", "n").lower()
        if proceed != "y":
            sys.exit(4)

    target_width_str = ask("Ziel-Bildbreite in Pixel (Höhe proportional)", "1920")
    try:
        target_width = max(1, int(target_width_str))
    except ValueError:
        print("Fehler: Zielbreite muss eine Ganzzahl sein.")
        sys.exit(5)

    quality_default = "80" if out_fmt in {"webp", "jpg", "avif"} else "0"
    quality_str = ask("Qualität (0-100, höher = besser; PNG ignoriert es)", quality_default)
    try:
        quality = min(100, max(0, int(quality_str)))
    except ValueError:
        print("Fehler: Qualität muss 0-100 sein.")
        sys.exit(6)

    pdf_zoom_str = ask("PDF-Render-Zoom (1.0 ≈ 72 DPI, 2.0 ≈ 144 DPI)", "2.0")
    try:
        pdf_zoom = max(0.1, float(pdf_zoom_str))
    except ValueError:
        print("Fehler: PDF-Zoom muss Zahl sein.")
        sys.exit(7)

    print("\nStarte Verarbeitung …\n")
    walk_and_convert(
        in_dir=in_dir,
        out_dir=out_dir,
        include_exts=include_exts,
        out_fmt=out_fmt,
        target_width=target_width,
        quality=quality,
        pdf_zoom=pdf_zoom,
        prefix=prefix,
    )
    print("\nFertig.")


if __name__ == "__main__":
    main()
