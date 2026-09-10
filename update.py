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

"""Проверка обновлений через SourceForge Release API (best_release.json).

Модуль самодостаточен — использует только стандартную библиотеку
(urllib, json, re) и не знает ничего про Tkinter или структуру главного
приложения. Сетевой вызов синхронный и блокирующий, поэтому вызывающий
код обязан запускать check_for_update() в фоновом потоке, а не в
GUI-потоке.

Приложение анонимно (без ключа) обращается к публичному API
https://sourceforge.net/projects/<project>/best_release.json — он
отдаёт информацию о файле, помеченном на SourceForge как релиз по
умолчанию (см. https://sourceforge.net/p/forge/documentation/Using%20the%20Release%20API/).
Готового поля с номером версии там нет — версия зашита в имени папки
релиза (у этого проекта релизы лежат в папках вида /files/v1.17.3/…,
см. https://sourceforge.net/projects/formatix-image-converter/files/),
поэтому она извлекается регуляркой из пути до файла.
"""

import json
import re
import urllib.request
import urllib.error

SF_PROJECT   = "formatix-image-converter"
API_URL      = f"https://sourceforge.net/projects/{SF_PROJECT}/best_release.json"
RELEASES_URL = f"https://sourceforge.net/projects/{SF_PROJECT}/files/"

# Версия — это имя папки релиза сразу после /files/, например
# ".../files/v1.17.3/v1.17.3 source code.zip/download" -> "v1.17.3".
_VERSION_FOLDER_RE = re.compile(r"/files/([^/]+)/")


def parse_version(version_str):
    """'v1.16.0' / '1.16.0' -> (1, 16, 0) для сравнения кортежами.

    Нечисловые хвосты внутри сегмента (например, '0-beta') обрезаются
    до первых цифр — этого достаточно для сравнения релизов проекта,
    полноценный semver-парсинг здесь избыточен.
    """
    version_str = version_str.strip().lstrip("vV")
    parts = []
    for chunk in version_str.split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote_version, current_version):
    """True, если remote_version строго новее current_version."""
    return parse_version(remote_version) > parse_version(current_version)


def _extract_version(release_entry):
    """Достаёт 'v1.17.3' из filename/url записи best_release.json.

    release_entry — это либо весь JSON-объект (для релиза по умолчанию),
    либо под-объект platform_releases.<platform> — у обоих есть filename
    с путём вида '/formatix-image-converter/files/v1.17.3/имя/download'.
    """
    if not isinstance(release_entry, dict):
        return None
    for key in ("filename", "url"):
        value = release_entry.get(key)
        if not value:
            continue
        match = _VERSION_FOLDER_RE.search(value)
        if match:
            return match.group(1)
    return None


def fetch_latest_release(timeout=5):
    """Запрашивает последний релиз с SourceForge.

    Возвращает (version, url) или None при любой ошибке (нет сети,
    таймаут, проект недоступен, формат ответа не распознан и т.д.) —
    ошибки сети не должны быть заметны пользователю, поэтому все они
    гасятся молча.
    """
    req = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "Formatix-Update-Check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    # Сначала пробуем релиз по умолчанию (top-level), затем — Windows-сборку
    # из platform_releases, если верхний уровень версию не дал.
    version = _extract_version(data)
    if not version:
        version = _extract_version(
            (data.get("platform_releases") or {}).get("windows")
        )
    if not version:
        return None

    url = f"{RELEASES_URL}{version}/"
    return version, url


def check_for_update(current_version, timeout=5):
    """Синхронная проверка обновления — вызывать из фонового потока.

    Возвращает (tag_name, url) новой версии, если она новее current_version,
    иначе None (в том числе при любой сетевой ошибке).
    """
    result = fetch_latest_release(timeout=timeout)
    if result is None:
        return None
    tag, url = result
    if is_newer(tag, current_version):
        return tag, url
    return None
