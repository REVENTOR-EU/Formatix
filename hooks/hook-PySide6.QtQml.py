# Formatix build hook — overrides the built-in hook-PySide6.QtQml.
#
# The stock PyInstaller hook collects ALL QML plugin directories from the
# PySide6 installation (QtWebEngine, QtMultimedia, Qt3D, ...), inflating the
# bundle by ~200 MB. Formatix uses only QtQuick (+ Controls/Layouts/Dialogs/
# Effects/labs), so we collect only the whitelisted directories below.

import pathlib

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

# Top-level directories under PySide6/qml that our UI actually uses.
ALLOWED_QML_ROOTS = {"Qt", "QtQuick", "QtQml", "QtCore"}

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

info = pyside6_library_info
if info.version is not None:
    qml_src = pathlib.Path(info.location["QmlImportsPath"]).resolve()
    qml_dest = pathlib.PurePath(info.qt_rel_dir) / "qml"

    for qmldir_file in sorted(qml_src.rglob("qmldir")):
        plugin_dir = qmldir_file.parent
        rel = plugin_dir.relative_to(qml_src)
        top = rel.parts[0] if rel.parts else ""
        if top not in ALLOWED_QML_ROOTS:
            continue
        try:
            plugin_binaries, plugin_datas = info._process_qml_plugin(qmldir_file)
        except Exception:
            continue

        def dest_of(src):
            r = (src.relative_to(qml_src) if src.is_dir()
                 else src.relative_to(qml_src).parent)
            return qml_dest / r

        binaries += [(str(src), str(dest_of(src))) for src in plugin_binaries]
        datas += [(str(src), str(dest_of(src))) for src in plugin_datas]
