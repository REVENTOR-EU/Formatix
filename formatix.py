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

"""Точка входа Formatix — интерфейс Qt Quick (QML).

Вся реализация UI — в qmlapp/; движок конвертации — в converter.py.
Прежний интерфейс на Tkinter сохранён в formatix_legacy_tk.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qmlapp.main import main

if __name__ == "__main__":
    main()
