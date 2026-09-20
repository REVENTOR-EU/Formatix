<h1 align="center">
<sub>
<img src="icon.ico" height="38" width="38" alt="Logo">
</sub>
REVENTOR Image Compressor
</h1>

<p align="center">
  <strong>A fast, lightweight, and 100% offline batch image converter and resizer for Windows — rebuilt with a modern Qt Quick interface.</strong>
</p>

> **REVENTOR Image Compressor** is an actively developed fork of [Formatix](https://github.com/cyber-anderson/Formatix) by **cyber-anderson** (original author), featuring a completely new Apple-style Qt Quick interface, JPEG XL output, and a smarter compression engine. Original author repository: [cyber-anderson/Formatix](https://github.com/cyber-anderson/Formatix).

<a href="https://reventor.eu"><img src="assets/reventor_banner_black.svg" alt="REVENTOR"></a>

---

## What This Fork Adds

Compared to the original Formatix, this fork delivers:

* **Brand-new Qt Quick (QML) interface** — Apple-inspired design language, Inter typeface, rounded cards, hairline separators, and fluid animations. The old Tkinter UI is retired.
* **Live theme & language switching** — light and dark themes (Apple system palette) and 6 interface languages apply instantly from Settings, no restart needed.
* **JPEG XL (JXL) output** — next-generation compression alongside AVIF, WEBP and HEIC, with a working quality slider and target-file-size mode.
* **Skip-if-larger protection** — every result is encoded in memory first. If "compression" would produce a file larger than the original, nothing is written to disk at all.
* **Save next to the original** — leave the save folder empty and converted files land beside their sources; no folder prompt.
* **Delete originals after conversion** — optional, only on success, never when a result was skipped.
* **Folder drag & drop** — drop a folder (or a mixed selection) and every supported image inside it, including subfolders, is loaded.
* **Custom filename templates with live preview** — elements joined with an underscore separator (e.g. `photo_final_001.jpg`).
* **Per-side resize fields** — in proportional modes the auto-computed side is grayed out automatically.

---

## Key Features (inherited & improved)

* **9 Output Formats** — AVIF, WEBP, JPEG, HEIC/HEIF, JXL, PNG, BMP, TIFF, ICO
* **Multi-threaded Conversion** — multiple images converted simultaneously
* **Advanced Image Resizer** — 5 modes: proportional (by width/height), smart crop, custom dimensions
* **Color Profile Management** — ICC-based conversion via Pillow ImageCms
* **Multi-size ICO Generation** — automatic Windows icon packs
* **Adjustable Quality** — per-format quality slider, or target file size (KB/MB) with automatic quality search
* **Custom File Renaming** — presets or token-based template builder
* **Smart Conversion Cache** — identical settings are not converted twice
* **Safe Processing** — atomic file writes and overwrite protection
* **Multilingual UI** — English, Русский, Українська, Deutsch, Suomi, 中文
* **Light & Dark Mode**

---

## Requirements

* **OS:** Windows (pre-built portable `.exe`)
* **Python:** 3.10+ *(only required if running from source; developed and packaged on Python 3.14)*
* **Dependencies:** `Pillow`, `pillow-heif`, `pillow-jxl-plugin`, `PySide6`, `resvg-py`

---

## Installation & Running

### Option 1 — Portable Executable (Windows)
Download the latest `REVENTOR-Image-Compressor.exe` from [Releases](https://github.com/REVENTOR-EU/Formatix/releases) and run it directly. No installation required.

### Option 2 — Run from Source

```bash
pip install Pillow pillow-heif pillow-jxl-plugin PySide6 resvg-py
python formatix.py
```

| File | Description |
| :--- | :--- |
| `formatix.py` | Entry point (Qt Quick UI) |
| `qmlapp/` | QML interface implementation |
| `converter.py` | Conversion engine (shared) |
| `formatix_legacy_tk.py` | Legacy Tkinter UI |

---

## Output Formats

| Format | Compression | Notes |
| :--- | :--- | :--- |
| **AVIF** | Lossy (Adjustable) | Next-generation; superior compression at high visual quality |
| **JXL** | Lossy (Adjustable) | JPEG XL — the successor to JPEG |
| **WEBP** | Lossy (Adjustable) | Great balance of size and browser support |
| **HEIC** | Lossy (Adjustable) | Apple's format |
| **JPEG** | Lossy (Adjustable) | Universal classic |
| **PNG / BMP / TIFF / ICO** | Lossless | Full quality; quality slider not applicable |

---

## FAQ

**Q: Which format should I choose for maximum compression?**

**JXL or AVIF** — both deliver the smallest files with excellent visual quality. At quality 80, files are often 4× smaller than the original with no visible difference. Files that wouldn't benefit from conversion are skipped automatically.

**Q: Where are my converted files saved?**

Next to the originals by default — unless you pick a save folder.

**Q: What happens if "compression" makes a file bigger?**

Nothing is written. The result is encoded in memory, and only files that are actually smaller are saved; the rest are reported as skipped (⊘).

---

## Credits

* **[cyber-anderson](https://github.com/cyber-anderson)** — original author of [Formatix](https://github.com/cyber-anderson/Formatix), creator of the conversion engine this project builds on
* **[REVENTOR](https://reventor.eu)** — Qt Quick interface, JPEG XL support, compression engine improvements, Windows builds

---

## License

This project is licensed under the [GPL-3.0 License](https://github.com/REVENTOR-EU/Formatix/blob/main/LICENSE).
