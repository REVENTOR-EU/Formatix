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

"""Шрифт интерфейса: загрузка Inter и системные запасные варианты.

Модуль самодостаточен и не зависит от главного файла приложения. Он
пытается загрузить входящие в поставку TTF-файлы Inter (fonts/) как
приватные шрифты процесса — только для нашего приложения, без установки
в систему. Если это не удалось (другая ОС, файлы отсутствуют), FONT_UI
получает системный шрифт с похожим нейтральным характером.

На Windows шрифты регистрируются через AddFontResourceExW с флагом
FR_PRIVATE; на других платформах приватной регистрации без установки
нет, поэтому сразу используем запасные системные семейства.
"""

import os
import sys

# Ключ шрифта должен совпадать с именем семейства внутри TTF-файлов
FONT_UI   = "Inter"
FONT_MONO = "Consolas"


def _fonts_dir():
    """Папка fonts/ рядом с приложением (или внутри PyInstaller-бандла)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "fonts")


def _register_windows():
    """Регистрирует TTF-файлы из fonts/ как приватные шрифты процесса.

    Возвращает True, если хотя бы один файл успешно загружен.
    """
    import ctypes
    FR_PRIVATE = 0x10
    loaded_any = False
    for name in os.listdir(_fonts_dir()):
        if not name.lower().endswith(".ttf"):
            continue
        path = os.path.join(_fonts_dir(), name)
        # NP: возвращаемое значение — число добавленных шрифтов (0 = отказ)
        if ctypes.windll.gdi32.AddFontResourceExW(path, FR_PRIVATE, 0) > 0:
            loaded_any = True
    return loaded_any


def _init_fonts():
    global FONT_UI, FONT_MONO
    if sys.platform == "win32":
        try:
            if _register_windows():
                return  # FONT_UI уже "Inter"
        except Exception:
            pass
        FONT_UI = "Segoe UI"
    elif sys.platform == "darwin":
        # Helvetica Neue предустановлен в macOS и визуально ближе всего
        # к Inter — отдельная загрузка шрифтов там всё равно не проще.
        FONT_UI = "Helvetica Neue"
        FONT_MONO = "Menlo"
    else:
        FONT_UI = "DejaVu Sans"
        FONT_MONO = "DejaVu Sans Mono"


_init_fonts()
