# Batch Asset Converter for WordPress

A Python script for batch converting images and PDFs into web-optimized formats with WordPress-friendly filenames.

## Features

- **Multi-format Support**: Convert TIF, JPG, PNG, BMP, GIF, and PDF files
- **Modern Output Formats**: AVIF, WebP, PNG, or JPG
- **WordPress-Optimized Naming**: Automatic SEO-friendly slug generation
- **Filename Prefix Support**: Optional prefix for organized file naming (e.g., `abc123-`)
- **Smart Output Directory**: Defaults to `output-web` subfolder in source directory
- **Smart Image Processing**: Auto-resize, EXIF orientation correction, color mode handling
- **Large Image Support**: Handles high-resolution images up to 300 megapixels
- **PDF to Image**: Convert multi-page PDFs to individual images
- **Collision-Safe**: Automatic handling of duplicate filenames
- **Quality Control**: Configurable compression and quality settings

## Installation

### Requirements

```bash
pip install Pillow
```

### Optional Dependencies

For AVIF support:
```bash
pip install pillow-avif-plugin
```

For PDF conversion:
```bash
pip install pymupdf
```

## Usage

Run the script interactively:

```bash
python batch_convert_assets.py
```

You'll be prompted for:

1. **Source Directory**: Path to input files (default: current directory)
2. **Output Directory**: Path for converted files (default: `<source-dir>/output-web`)
3. **Filename Prefix**: Optional prefix for all output files (e.g., `ABC123`)
4. **File Extensions**: Comma-separated list (default: `tif,jpg,jpeg,png,pdf`)
5. **Target Format**: Output format - `avif`, `webp`, `png`, or `jpg` (default: `webp`)
6. **Target Width**: Maximum width in pixels (default: `1920`)
7. **Quality**: Compression quality 0-100 (default: `80`)
8. **PDF Zoom**: Rendering resolution for PDFs (default: `2.0` ≈ 144 DPI)

### Example Session

```
=== Batch-Konverter: TIF/JPG/PNG/PDF -> AVIF/WEBP/PNG/JPG (WordPress-optimierte Namen) ===

Quellordner eingeben [.]: /path/to/images
Zielordner eingeben [/path/to/images/output-web]:
Dateinamen-Prefix (z.B. ABC123, optional - Enter für keinen) []: PRJ001
  → Normalisierter Prefix: 'prj001-'
Dateimuster (Komma-getrennt), z.B. tif,jpg,png,pdf [tif,jpg,jpeg,png,pdf]: png,jpg
Zielformat (avif/webp/png/jpg) [webp]: webp
Ziel-Bildbreite in Pixel (Höhe proportional) [1920]: 1920
Qualität (0-100, höher = besser; PNG ignoriert es) [80]: 85
PDF-Render-Zoom (1.0 ≈ 72 DPI, 2.0 ≈ 144 DPI) [2.0]: 2.0

Starte Verarbeitung …
```

## How It Works

### WordPress-Friendly Naming

The script automatically converts filenames to WordPress-compatible slugs:

| Original Filename | Without Prefix | With Prefix `abc123` |
|------------------|----------------|----------------------|
| `Mein Bild Ü.jpg` | `mein-bild-ue.webp` | `abc123-mein-bild-ue.webp` |
| `Café_Photo.png` | `cafe-photo.webp` | `abc123-cafe-photo.webp` |
| `Straße 123.tif` | `strasse-123.webp` | `abc123-strasse-123.webp` |

**Transformations:**
- German umlauts: ä→ae, ö→oe, ü→ue, ß→ss
- Removes diacritics and special characters
- Converts to lowercase
- Replaces spaces and special chars with hyphens
- Optionally adds prefix at the beginning (normalized to lowercase, alphanumeric only)
- Handles duplicate names with `-001`, `-002` suffixes

**Prefix Feature:**
- Enter a prefix like `ABC123` or `Project-42` when prompted
- Normalized to: `abc123-` or `project42-`
- Smart detection: won't duplicate if filename already has the prefix
- Press Enter to skip prefix (optional)

### Image Processing

- **Auto-resize**: Images wider than target width are scaled down proportionally
- **EXIF correction**: Automatically fixes image orientation based on EXIF data
- **Color mode handling**: Converts CMYK to RGB, handles transparency appropriately
- **Format-specific optimization**:
  - **JPG**: Progressive encoding, 4:2:0 chroma subsampling, optimize flag
  - **PNG**: Compression level 6
  - **WebP**: Method 6 for better compression
  - **AVIF**: Quality-based encoding

### PDF Conversion

- Each PDF page becomes a separate image file
- Naming convention: `filename-p001.webp`, `filename-p002.webp`, etc.
- Configurable rendering resolution (zoom factor)
- Supports both RGB and RGBA rendering

## Output Structure

All converted files are placed in the output directory with flat structure (no subdirectories), making them easy to bulk upload to WordPress media library.

## Error Handling

The script will:
- Skip unsupported file types
- Continue processing if individual files fail
- Display error messages for failed conversions
- Warn if optional dependencies are missing

## Technical Details

### Supported Input Formats
- Images: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.gif`
- Documents: `.pdf` (requires PyMuPDF)

### Supported Output Formats
- **AVIF**: Modern, highly compressed (requires pillow-avif-plugin)
- **WebP**: Modern, good browser support
- **PNG**: Lossless, best for graphics with transparency
- **JPG**: Lossy, universal compatibility

### Performance Tips
- Larger zoom values for PDFs result in better quality but larger files
- Quality 80-85 offers good balance for WebP/AVIF
- Use WebP for broad compatibility, AVIF for maximum compression

## License

This script is provided as-is for personal and commercial use.

## Troubleshooting

### "Pillow ist nicht installiert"
Install Pillow: `pip install Pillow`

### "AVIF wird nicht unterstützt"
Install AVIF plugin: `pip install pillow-avif-plugin`

### "PDF-Konvertierung benötigt PyMuPDF"
Install PyMuPDF: `pip install pymupdf`

### Images appear rotated
The script automatically handles EXIF orientation. If images still appear rotated, the source file may have incorrect metadata.

### Low quality output
Increase the quality parameter (recommended: 85-95 for important images)

### DecompressionBombWarning for large images
The script handles images up to 300 megapixels. If you need to process even larger images, this limit can be adjusted in the code.

## Contributing

Feel free to modify and extend this script for your needs. Common enhancements:
- Add command-line argument support
- Implement parallel processing for faster conversion
- Add watermarking capabilities
- Support additional metadata preservation
