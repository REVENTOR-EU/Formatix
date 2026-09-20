# Formatix Image Converter
# Copyright (C) 2026 cyber-anderson
# https://github.com/cyber-anderson/Formatix
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Новый Qt Quick (QML) интерфейс Formatix поверх существующего движка.

Вся логика конвертации живёт в converter.py и переиспользуется без
изменений (convert_one, кэш, шаблоны имён, «рядом с оригиналом»,
удаление оригиналов). Этот модуль содержит только Backend(QObject) —
мост между QML и движком — и точку входа приложения.

Запуск:  python qmlapp/main.py
"""

import os
import sys
import json
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import (QObject, QAbstractListModel, QModelIndex, Qt, QUrl,
                            Property, Signal, Slot, QTimer, QByteArray)
from PySide6.QtGui import QGuiApplication, QFont, QFontDatabase, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from converter import (
    FORMATS, IMG_EXTS, format_size, get_image_res_str,
    render_filename_template, generate_unique_filename, convert_one,
)
from localization import LANGUAGES, STRINGS, detect_system_lang, APP_NAME
from update import check_for_update

VERSION = "2.0.0"
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".formatix_image_converter_settings.json")
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def detect_system_theme():
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            import subprocess
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                               capture_output=True, text=True, timeout=2)
            if r.returncode == 0 and "dark" in r.stdout.lower():
                return "dark"
            return "light"
        except Exception:
            pass
    return "dark"


# ── палитры (Apple system colors) ─────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#1a1a1c", "bg2": "#232326", "bg3": "#2c2c2e", "card": "#323234",
        "accent": "#0a84ff", "accentHover": "#409cff", "red": "#ff453a",
        "green": "#30d158", "fg": "#f5f5f7", "fg2": "#98989e", "fg3": "#636366",
        "border": "#3d3d40", "tint": "#1a2c44",
    },
    "light": {
        "bg": "#f5f5f7", "bg2": "#ececf0", "bg3": "#e3e3e8", "card": "#ffffff",
        "accent": "#0071e3", "accentHover": "#3395ff", "red": "#ff3b30",
        "green": "#248a3d", "fg": "#1d1d1f", "fg2": "#6e6e73", "fg3": "#aeaeb2",
        "border": "#d9d9de", "tint": "#e9f2fd",
    },
}


class SimpleModel(QAbstractListModel):
    """Базовый list-model с динамическим набором ролей."""
    _roles = {}

    def __init__(self, roles):
        super().__init__()
        # Номера ролей обязаны начинаться с Qt.UserRole — иначе конфликт
        # со встроенными ролями Qt (DisplayRole и т.п.) и пустые строки в QML
        self._roles = {Qt.UserRole + i: QByteArray(r.encode())
                       for i, r in enumerate(roles)}
        self._rows = []

    def roleNames(self):
        return dict(self._roles)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        role_name = self._roles.get(role)
        if role_name is None:
            return None
        return self._rows[index.row()].get(bytes(role_name).decode(), None)

    def reset(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class Backend(QObject):
    converted = Signal(int, str, str, str, bool, bool)  # idx, name, res, size, ok, skipped

    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        self._data_lock = threading.Lock()
        self._converted_cache = {}
        self._files = []                 # [{path,name,res,size}]
        self._results = []               # [{ok,name,res,size}]
        self._gui_queue = queue.Queue()
        self._running = False
        self._stop_requested = False
        self._overwrite_answer = None

        # ── восстановление настроек ─────────────────────────────────────────
        s = self._settings
        self._lang = s.get("lang") or detect_system_lang()
        self._theme = s.get("theme") or detect_system_theme()
        # Удобно для скриншотов/тестов: FORMATIX_THEME=dark|light
        self._theme = os.environ.get("FORMATIX_THEME", self._theme)
        if self._theme not in THEMES:
            self._theme = "dark"
        self._fmt = s.get("fmt", "AVIF")
        if self._fmt not in FORMATS:
            self._fmt = FORMATS[0]
        self._quality = int(s.get("quality", 85))
        self._quality_mode = s.get("quality_mode", "percent")
        self._target_size_val = str(s.get("target_size_val", 500))
        self._target_size_unit = s.get("target_size_unit", "KB")
        self._resize_key = s.get("resize_mode_key", "no_change")
        self._delete_original = bool(s.get("delete_original", False))
        out_dir = s.get("out_dir", "")
        self._out_dir = out_dir if out_dir and os.path.isdir(out_dir) else ""
        self._fn_preset = s.get("filename_preset", "original")
        self._tokens = [t for t in s.get("filename_tokens", [])
                        if isinstance(t, dict) and t.get("type") in ("name", "index", "date", "text")]
        self._w_val = ""
        self._h_val = ""
        self._status = self.trKey("ready")
        self._status_err = ""
        self._progress = 0
        self._total_dst = 0
        self._lang_rev = 0
        self._update_state = ""

        self.files_model = SimpleModel(["name", "res", "size"])
        self.results_model = SimpleModel(["ok", "name", "res", "size", "skipped"])
        self._refresh_files_model()

        self.converted.connect(self._on_converted)
        self._drain_timer = QTimer(self)
        self._drain_timer.timeout.connect(self._drain_queue)
        self._drain_timer.start(80)

    # ── локализация ───────────────────────────────────────────────────────────
    @Slot(str, result=str)
    def trKey(self, key):
        s = STRINGS.get(self._lang, STRINGS["en"])
        return s.get(key, STRINGS["en"].get(key, key))

    @Slot(result=str)
    def langName(self):
        return LANGUAGES[self._lang]

    @Slot(result=int)
    def langRev(self):
        return self._lang_rev

    @Slot(str)
    def setLangByName(self, name):
        for code, lname in LANGUAGES.items():
            if lname == name:
                if code != self._lang:
                    self._lang = code
                    self._settings["lang"] = code
                    self._lang_rev += 1
                    self.langRevChanged.emit()
                    self._save()
                break

    @Slot(result="QVariantList")
    def langNames(self):
        return list(LANGUAGES.values())

    # ── тема ──────────────────────────────────────────────────────────────────
    def _theme_color(self, key):
        return THEMES[self._theme][key]

    def _set_theme(self, theme):
        if theme in THEMES and theme != self._theme:
            self._theme = theme
            self._settings["theme"] = theme
            self._save()
            self.themeChanged.emit()

    @Slot(str)
    def setTheme(self, theme):
        self._set_theme(theme)

    themeChanged = Signal()
    version = Property(str, lambda self: VERSION, constant=True)
    bg = Property(str, lambda self: self._theme_color("bg"), notify=themeChanged)
    bg2 = Property(str, lambda self: self._theme_color("bg2"), notify=themeChanged)
    bg3 = Property(str, lambda self: self._theme_color("bg3"), notify=themeChanged)
    card = Property(str, lambda self: self._theme_color("card"), notify=themeChanged)
    accent = Property(str, lambda self: self._theme_color("accent"), notify=themeChanged)
    accentHover = Property(str, lambda self: self._theme_color("accentHover"), notify=themeChanged)
    red = Property(str, lambda self: self._theme_color("red"), notify=themeChanged)
    green = Property(str, lambda self: self._theme_color("green"), notify=themeChanged)
    fg = Property(str, lambda self: self._theme_color("fg"), notify=themeChanged)
    fg2 = Property(str, lambda self: self._theme_color("fg2"), notify=themeChanged)
    fg3 = Property(str, lambda self: self._theme_color("fg3"), notify=themeChanged)
    border = Property(str, lambda self: self._theme_color("border"), notify=themeChanged)
    tint = Property(str, lambda self: self._theme_color("tint"), notify=themeChanged)
    themeName = Property(str, lambda self: self._theme, notify=themeChanged)

    # ── файлы ─────────────────────────────────────────────────────────────────
    filesChanged = Signal()
    filesCount = Property(int, lambda self: len(self._files), notify=filesChanged)
    srcBytes = Property(str, lambda self: format_size(sum(f["size"] for f in self._files)), notify=filesChanged)

    def _refresh_files_model(self):
        self.files_model.reset([{"name": f["name"], "res": f["res"], "size": format_size(f["size"])}
                                for f in self._files])
        self.filesChanged.emit()

    @Slot("QVariantList")
    def addFiles(self, urls):
        """Принимает пути из QML: элементы могут быть QUrl (FileDialog,
        DropArea) или строками (file:// и обычные пути)."""
        added = False
        for u in urls:
            if isinstance(u, QUrl):
                p = u.toLocalFile()
            elif isinstance(u, str) and "://" in u:
                p = QUrl(u).toLocalFile()
            else:
                p = str(u)
            p = os.path.normpath(p.strip())
            if not p or p in {f["path"] for f in self._files}:
                continue
            if os.path.splitext(p)[1].lower() in IMG_EXTS and os.path.isfile(p):
                self._files.append({
                    "path": p,
                    "name": os.path.basename(p),
                    "res": get_image_res_str(p),
                    "size": os.path.getsize(p),
                })
                added = True
        if added:
            self._refresh_files_model()

    @Slot(int)
    def removeFile(self, idx):
        if 0 <= idx < len(self._files):
            del self._files[idx]
            self._refresh_files_model()

    @Slot()
    def clearFiles(self):
        self._files.clear()
        self._results.clear()
        self.results_model.reset([])
        self._svg_size_cache = getattr(self, "_svg_size_cache", {})
        self._converted_cache.clear()
        self._total_dst = 0
        self._refresh_files_model()
        self.dstBytesChanged.emit()

    filesModel = Property(QObject, lambda self: self.files_model, constant=True)
    resultsModel = Property(QObject, lambda self: self.results_model, constant=True)

    # ── настройки-свойства ────────────────────────────────────────────────────
    def _save(self):
        save_settings(self._settings)

    fmtChanged = Signal()
    def _get_fmt(self):
        return self._fmt
    def _set_fmt(self, v):
        if v in FORMATS and v != self._fmt:
            self._fmt = v
            self._settings["fmt"] = v
            self._save()
            self.fmtChanged.emit()
    fmt = Property(str, _get_fmt, _set_fmt, notify=fmtChanged)


    @Slot(result="QVariantList")
    def formats(self):
        return list(FORMATS)

    qualityChanged = Signal()
    def _get_quality(self):
        return self._quality
    def _set_quality(self, v):
        v = max(10, min(99, int(v)))
        if v != self._quality:
            self._quality = v
            self._settings["quality"] = v
            self._save()
            self.qualityChanged.emit()
    quality = Property(int, _get_quality, _set_quality, notify=qualityChanged)


    qualityModeChanged = Signal()
    def _get_qualityMode(self):
        return self._quality_mode
    def _set_qualityMode(self, v):
        if v in ("percent", "size") and v != self._quality_mode:
            self._quality_mode = v
            self._settings["quality_mode"] = v
            self._save()
            self.qualityModeChanged.emit()
    qualityMode = Property(str, _get_qualityMode, _set_qualityMode, notify=qualityModeChanged)


    targetSizeChanged = Signal()
    def _get_targetSizeVal(self):
        return self._target_size_val
    def _set_targetSizeVal(self, v):
        v = "".join(ch for ch in str(v) if ch.isdigit())[:6]
        if v and v != self._target_size_val:
            self._target_size_val = v
            self._settings["target_size_val"] = int(v)
            self._save()
            self.targetSizeChanged.emit()
    targetSizeVal = Property(str, _get_targetSizeVal, _set_targetSizeVal, notify=targetSizeChanged)


    @Slot(str)
    def setTargetUnit(self, unit):
        if unit in ("KB", "MB") and unit != self._target_size_unit:
            self._target_size_unit = unit
            self._settings["target_size_unit"] = unit
            self._save()
            self.targetSizeChanged.emit()

    unitChanged = Signal()
    @Property(str, notify=unitChanged)
    def targetUnit(self):
        return self._target_size_unit

    resizeKeyChanged = Signal()
    def _get_resizeModeKey(self):
        return self._resize_key
    def _set_resizeModeKey(self, key):
        if key in ("no_change", "prop_width", "prop_height", "smart_crop", "custom") and key != self._resize_key:
            self._resize_key = key
            self._settings["resize_mode_key"] = key
            self._save()
            self.resizeKeyChanged.emit()
    resizeModeKey = Property(str, _get_resizeModeKey, _set_resizeModeKey, notify=resizeKeyChanged)

    @Slot(result="QVariantList")
    def resizeModes(self):
        """Список [локализованное имя, ключ] для комбо разрешения."""
        s = STRINGS.get(self._lang, STRINGS["en"])
        return [[s["resize_no_change"], "no_change"], [s["resize_prop_w"], "prop_width"],
                [s["resize_prop_h"], "prop_height"], [s["resize_crop"], "smart_crop"],
                [s["resize_custom"], "custom"]]

    @Slot(str, result=str)
    def resizeModeName(self, key):
        m = dict(self.resizeModes())
        return m.get(key, key)

    wChanged = Signal()
    def _get_wVal(self):
        return self._w_val
    def _set_wVal(self, v):
        v = str(v).strip()
        if v != self._w_val:
            self._w_val = v
            self.wChanged.emit()
    wVal = Property(str, _get_wVal, _set_wVal, notify=wChanged)


    hChanged = Signal()
    def _get_hVal(self):
        return self._h_val
    def _set_hVal(self, v):
        v = str(v).strip()
        if v != self._h_val:
            self._h_val = v
            self.hChanged.emit()
    hVal = Property(str, _get_hVal, _set_hVal, notify=hChanged)


    deleteOriginalChanged = Signal()
    def _get_deleteOriginal(self):
        return self._delete_original
    def _set_deleteOriginal(self, v):
        if bool(v) != self._delete_original:
            self._delete_original = bool(v)
            self._settings["delete_original"] = self._delete_original
            self._save()
            self.deleteOriginalChanged.emit()
    deleteOriginal = Property(bool, _get_deleteOriginal, _set_deleteOriginal, notify=deleteOriginalChanged)


    outDirChanged = Signal()
    def _get_outDir(self):
        return self._out_dir
    def _set_outDir(self, v):
        v = str(v)
        if v != self._out_dir:
            self._out_dir = v
            self._settings["out_dir"] = v if v and os.path.isdir(v) else ""
            self._save()
            self.outDirChanged.emit()
    outDir = Property(str, _get_outDir, _set_outDir, notify=outDirChanged)


    @Property(str, notify=outDirChanged)
    def outDirDisplay(self):
        return self._out_dir if self._out_dir else self.trKey("folder_placeholder")

    fnPresetChanged = Signal()
    def _get_fnPreset(self):
        return self._fn_preset
    def _set_fnPreset(self, v):
        if v in ("original", "number", "date", "custom") and v != self._fn_preset:
            self._fn_preset = v
            self._settings["filename_preset"] = v
            self._save()
            self.fnPresetChanged.emit()
    fnPreset = Property(str, _get_fnPreset, _set_fnPreset, notify=fnPresetChanged)


    tokensChanged = Signal()
    def _get_tokens(self):
        return list(self._tokens)
    def _set_tokens(self, v):
        self._tokens = [dict(t) for t in v if isinstance(t, dict)]
        self._settings["filename_tokens"] = list(self._tokens)
        self._save()
        self.tokensChanged.emit()
    tokens = Property("QVariantList", _get_tokens, _set_tokens, notify=tokensChanged)


    @Slot(str)
    def addToken(self, kind):
        if kind == "text":
            return  # текст добавляется из поля ввода в QML: addTextToken
        self._tokens.append({"type": kind})
        self.tokens = self._tokens

    @Slot(str)
    def addTextToken(self, text):
        text = "".join(c for c in text if c not in '<>:"/\\|?*' and ord(c) >= 32).strip()
        if text:
            self._tokens.append({"type": "text", "value": text})
            self.tokens = self._tokens

    @Slot(int)
    def removeToken(self, idx):
        if 0 <= idx < len(self._tokens):
            del self._tokens[idx]
            self.tokens = self._tokens

    @Slot(result=str)
    def namePreview(self):
        return render_filename_template("photo", 1, self._fn_preset, self._tokens) + ".jpg"

    # ── статус и прогресс ─────────────────────────────────────────────────────
    statusChanged = Signal()
    def _get_status(self):
        return self._status
    def _set_status(self, v):
        self._status = str(v)
        self.statusChanged.emit()
    status = Property(str, _get_status, _set_status, notify=statusChanged)


    statusErrChanged = Signal()
    def _get_statusErr(self):
        return self._status_err
    def _set_statusErr(self, v):
        self._status_err = str(v)
        self.statusErrChanged.emit()
    statusErr = Property(str, _get_statusErr, _set_statusErr, notify=statusErrChanged)


    progressChanged = Signal()
    def _get_progress(self):
        return self._progress
    def _set_progress(self, v):
        self._progress = int(v)
        self.progressChanged.emit()
    progress = Property(int, _get_progress, _set_progress, notify=progressChanged)


    runningChanged = Signal()
    @Property(bool, notify=runningChanged)
    def running(self):
        return self._running

    dstBytesChanged = Signal()
    @Property(str, notify=dstBytesChanged)
    def dstBytes(self):
        return format_size(self._total_dst)

    # ── действия ──────────────────────────────────────────────────────────────
    @Slot()
    def convert(self):
        if self._running or not self._files:
            self.status = self.trKey("warn_no_files") if not self._files else self._status
            return
        # Валидация: SVG без размеров в режимах crop/custom
        if self._resize_key in ("smart_crop", "custom"):
            for f in self._files:
                if f["path"].lower().endswith(".svg"):
                    w, h = _svg_size(f["path"])
                    if not w:
                        self.statusErr = self.trKey("svg_no_size_msg")
                        return
        w = int(self._w_val) if self._w_val.isdigit() else 0
        h = int(self._h_val) if self._h_val.isdigit() else 0
        if self._resize_key == "custom" and (not w or not h):
            self.statusErr = self.trKey("warn_bad_size")
            return
        if self._resize_key == "prop_width" and not w:
            self.statusErr = self.trKey("warn_bad_size")
            return
        if self._resize_key == "prop_height" and not h:
            self.statusErr = self.trKey("warn_bad_size")
            return
        target_bytes = None
        if self._quality_mode == "size" and self._fmt in ("JPEG", "WEBP", "HEIC", "AVIF", "JXL"):
            num = int(self._target_size_val) if self._target_size_val.isdigit() else 0
            if num <= 0:
                self.statusErr = self.trKey("warn_bad_target_size")
                return
            target_bytes = num * (1024 * 1024 if self._target_size_unit == "MB" else 1024)
        # Проверка конфликтов имён (по «чистому» имени, в папке назначения)
        ext = ".jpg" if self._fmt == "JPEG" else f".{self._fmt.lower()}"
        existing = []
        seen = set()
        for i, f in enumerate(self._files, start=1):
            base = render_filename_template(os.path.splitext(f["name"])[0], i, self._fn_preset, self._tokens)
            plain = base + ext
            pdir = self._out_dir or os.path.dirname(f["path"])
            if plain.lower() in seen:
                continue
            seen.add(plain.lower())
            if os.path.exists(os.path.join(pdir, plain)):
                existing.append(plain)
        if existing:
            preview = "\n".join(existing[:5])
            if len(existing) > 5:
                preview += self.trKey("overwrite_more").format(n=len(existing) - 5)
            self.askOverwrite.emit(preview)
            return
        self._run_convert(False)

    askOverwrite = Signal(str)

    @Slot(str, result=str)
    def overwriteText(self, names):
        return self.trKey("overwrite_msg").format(names=names)

    @Slot(bool)
    def overwriteAnswer(self, allowed):
        if allowed:
            self._run_convert(True)

    @Slot()
    def stopConvert(self):
        self._stop_requested = True

    def _run_convert(self, allow_overwrite):
        fmt = self._fmt
        ext = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"
        if self._quality_mode == "size" and self._fmt in ("JPEG", "WEBP", "HEIC", "AVIF", "JXL"):
            num = int(self._target_size_val)
            target_bytes = num * (1024 * 1024 if self._target_size_unit == "MB" else 1024)
            q_part = f"tgt:{target_bytes}"
        else:
            target_bytes = None
            q_part = f"q:{self._quality}"
        fn_part = f"fn:{self._fn_preset}:{self._tokens}"
        resize_key = self._resize_key
        w = int(self._w_val) if self._w_val.isdigit() else 0
        h = int(self._h_val) if self._h_val.isdigit() else 0
        out_dir = self._out_dir or None
        delete_original = self._delete_original
        files = [dict(f) for f in self._files]
        preset, tokens = self._fn_preset, list(self._tokens)
        quality = self._quality
        cache, lock = self._converted_cache, self._data_lock

        self._results.clear()
        self.results_model.reset([])
        self._total_dst = 0
        self.dstBytesChanged.emit()
        self._stop_requested = False
        self._running = True
        self.runningChanged.emit()
        self.statusErr = ""
        self._progress = 0
        self.progressChanged.emit()

        def worker():
            total = len(files)
            cfg_tpl = f"fmt:{fmt}|{q_part}|dir:{{}}|mode:{resize_key}|w:{w}|h:{h}|{fn_part}"
            workers_n = min(os.cpu_count() or 4, 8)
            reserved = {}
            alloc = {}
            for i, f in enumerate(files, start=1):
                fdir = out_dir or os.path.dirname(f["path"])
                base = render_filename_template(os.path.splitext(f["name"])[0], i, preset, tokens)
                alloc[f["path"]] = (fdir, generate_unique_filename(
                    fdir, base, ext, reserved.setdefault(fdir, set()), allow_overwrite=allow_overwrite))
            pool = ThreadPoolExecutor(max_workers=workers_n)
            futures = {}
            done = 0
            ok = err = skipped_cnt = 0
            try:
                for f in files:
                    fdir, out_name = alloc[f["path"]]
                    fu = pool.submit(convert_one, f["path"], fdir, fmt, out_name, quality,
                                     resize_key, w, h, cfg_tpl.format(fdir), resize_key,
                                     "percent" if target_bytes is None else "size", target_bytes,
                                     cache=cache, lock=lock)
                    futures[fu] = f
                for fu in as_completed(futures):
                    res = fu.result()
                    f = futures[fu]
                    done += 1
                    # skip_larger обрабатывается внутри convert_one:
                    # результат больше оригинала на диск вообще не пишется
                    skipped = bool(res.get("skipped"))
                    if skipped:
                        skipped_cnt += 1
                    elif res["success"]:
                        ok += 1
                    else:
                        err += 1
                    # удаление оригинала после успешной конвертации
                    if res["success"] and delete_original and not skipped:
                        try:
                            if os.path.abspath(f["path"]) != os.path.abspath(res["out_path"]):
                                os.remove(f["path"])
                        except OSError:
                            pass
                    self.converted.emit(done - 1, res["out_name"], res["res_str"],
                                        res["size_str"], res["success"], skipped)
                    self._gui_queue.put({"done": done, "total": total,
                                         "name": os.path.basename(f["path"]),
                                         "size": res["f_size"], "ok": ok,
                                         "err": err, "skipped": skipped_cnt})
                    if self._stop_requested:
                        break
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            stopped = self._stop_requested
            self._gui_queue.put({"finish": True, "ok": ok, "err": err,
                                 "skipped": skipped_cnt,
                                 "stopped": stopped, "total": total})

        threading.Thread(target=worker, daemon=True).start()

    def _on_converted(self, idx, name, res, size, ok, skipped):
        rows = list(self.results_model._rows)
        rows.append({"ok": ok, "name": name, "res": res,
                     "size": (self.trKey("skipped_larger") if skipped else size),
                     "skipped": skipped})
        self.results_model.reset(rows)

    def _drain_queue(self):
        try:
            while True:
                msg = self._gui_queue.get_nowait()
                if "finish" in msg:
                    self._running = False
                    self.runningChanged.emit()
                    self._progress = 100
                    self.progressChanged.emit()
                    if msg["stopped"]:
                        self._status = f"■  {self.trKey('processing_btn')} — {msg['ok']}/{msg['total']}"
                    else:
                        self._status = (f"✔ {msg['ok']}"
                                    + (f"  ✘ {msg['err']}" if msg["err"] else "")
                                    + (f"  ⊘ {msg['skipped']}" if msg["skipped"] else ""))
                    self.statusChanged.emit()
                else:
                    self._progress = round(msg["done"] / msg["total"] * 100)
                    self.progressChanged.emit()
                    self._status = f"{msg['done']}/{msg['total']}  {msg['name'][:16]}"
                    self.statusChanged.emit()
                    self._total_dst += msg["size"]
                    self.dstBytesChanged.emit()
        except queue.Empty:
            pass

    @Slot()
    def openOutFolder(self):
        d = self._out_dir or (os.path.dirname(self._files[-1]["path"]) if self._files else "")
        if d and os.path.isdir(d):
            _open_path(d)

    # ── обновления ────────────────────────────────────────────────────────────
    updateStateChanged = Signal()
    @Property(str, notify=updateStateChanged)
    def updateState(self):
        return self._update_state

    @Slot()
    def checkUpdatesNow(self):
        def worker():
            res = check_for_update(VERSION)
            if res:
                tag, url = res
                self._update_state = self.trKey("update_ver_label").format(old=VERSION, new=tag)
                self._update_url = url
            else:
                self._update_state = self.trKey("update_up_to_date")
                self._update_url = ""
            self.updateStateChanged.emit()
        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def openUpdateUrl(self):
        u = getattr(self, "_update_url", "")
        if u:
            _open_path(u)


def _svg_size(path):
    from converter import get_svg_resolution_pure
    return get_svg_resolution_pure(path)


def _open_path(path):
    import subprocess
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _qt_message(mode, ctx, msg):
    print("QT:", msg, file=sys.stderr)
    sys.stderr.flush()


def main():
    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(_qt_message)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(os.path.join(APP_DIR, "icon.ico")))

    # Inter как шрифт по умолчанию для всего QML
    for w in ("Regular", "Medium", "SemiBold", "Bold", "Italic"):
        f = os.path.join(APP_DIR, "fonts", f"Inter-{w}.ttf")
        if os.path.exists(f):
            QFontDatabase.addApplicationFont(f)
    app.setFont(QFont("Inter", 10))

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("B", backend)
    engine.load(os.path.join(os.path.dirname(__file__), "qml", "Main.qml"))
    if not engine.rootObjects():
        sys.exit(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
