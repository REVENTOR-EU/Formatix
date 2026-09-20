// Formatix — Qt Quick UI (Apple-style)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Effects

ApplicationWindow {
    id: win
    width: 1120; height: 760
    minimumWidth: 980; minimumHeight: 640
    visible: true
    title: "Formatix Image Converter"
    color: B.bg

    // ── локализация: зависимость от B.langRev заставляет биндинги обновляться ──
    function tt(k) { B.langRev; return B.trKey(k) }

    // ── переиспользуемые компоненты ────────────────────────────────────────────
    component Hairline: Rectangle { color: B.border; height: 1 }

    component AppButton: Rectangle {
        id: root
        property string label: ""
        property bool filled: false
        property bool big: false
        property bool subtle: false
        property color baseColor: filled ? B.accent : B.bg3
        property color hoverColor: filled ? B.accentHover : B.border
        signal activated()
        radius: 9
        color: ma.containsMouse ? hoverColor : baseColor
        implicitWidth: lbl.implicitWidth + (big ? 44 : 28)
        implicitHeight: big ? 40 : 32
        scale: ma.pressed ? 0.97 : 1.0
        Behavior on scale { NumberAnimation { duration: 80 } }
        Behavior on color { ColorAnimation { duration: 120 } }
        Text {
            id: lbl
            anchors.centerIn: parent
            text: root.label
            color: root.filled ? "#ffffff" : B.fg
            font.pixelSize: root.big ? 14 : 13
            font.weight: Font.DemiBold
        }
        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.activated()
        }
    }

    component AppCombo: ComboBox {
        id: combo
        implicitHeight: 32
        font.pixelSize: 13
        background: Rectangle {
            radius: 8; color: B.card; border.color: combo.hovered ? B.accent : B.border; border.width: 1
        }
        contentItem: Text {
            text: combo.displayText
            color: B.fg; font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10; rightPadding: 24
            elide: Text.ElideRight
        }
        indicator: Text {
            text: "▾"; color: B.fg2; font.pixelSize: 12
            anchors.right: parent.right; anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
        }
        delegate: ItemDelegate {
            width: combo.width
            contentItem: Text { text: modelData; color: B.fg; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
            highlighted: combo.highlightedIndex === index
            background: Rectangle { color: highlighted ? B.tint : "transparent"; radius: 6 }
        }
        popup: Popup {
            y: combo.height + 4
            width: combo.width
            padding: 4
            background: Rectangle { color: B.card; radius: 10; border.color: B.border; border.width: 1 }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                currentIndex: combo.highlightedIndex
            }
        }
    }

    component SectionLabel: Text {
        color: B.fg2; font.pixelSize: 11; font.weight: Font.DemiBold
        font.letterSpacing: 0.8
    }

    component TogglePill: Rectangle {
        id: tp
        property string value: "percent"
        property var options: []
        signal picked(string v)
        implicitWidth: opts.width + 8
        implicitHeight: 26
        radius: 13
        color: B.bg3
        Row {
            id: opts
            anchors.centerIn: parent
            Repeater {
                model: tp.options
                Rectangle {
                    required property var modelData
                    property bool active: tp.value === modelData[0]
                    width: t.implicitWidth + 24; height: 22; radius: 11
                    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    color: active ? B.accent : "transparent"
                    Text {
                        id: t; anchors.centerIn: parent
                        text: parent.modelData[1]
                        color: parent.active ? "#fff" : B.fg2
                        font.pixelSize: 12; font.weight: Font.DemiBold
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: tp.picked(parent.modelData[0])
                    }
                }
            }
        }
    }

    component CheckRow: Item {
        id: cr
        property string label: ""
        property bool checked: false
        signal toggled()
        width: row.implicitWidth; height: 28
        Row {
            id: row; spacing: 10; anchors.verticalCenter: parent.verticalCenter
            Rectangle {
                width: 20; height: 20; radius: 6
                anchors.verticalCenter: parent.verticalCenter
                color: cr.checked ? B.accent : "transparent"
                border.color: cr.checked ? B.accent : B.fg3; border.width: 1.5
                Text {
                    anchors.centerIn: parent; text: "✓"; color: "#fff"; font.pixelSize: 12; font.bold: true
                    visible: cr.checked
                }
            }
            Text { text: cr.label; color: B.fg; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: cr.toggled() }
    }

    component Card: Rectangle {
        color: B.card; radius: 14; border.color: B.border; border.width: 1
    }

    // ── диалоги ────────────────────────────────────────────────────────────────
    FileDialog {
        id: fileDialog
        nameFilters: ["Images (*)"]
        fileMode: FileDialog.OpenFiles
        onAccepted: B.addFiles(selectedFiles)
    }
    FolderDialog {
        id: folderDialog
        onAccepted: B.outDir = selectedFolder
    }
    Dialog {
        id: overwriteDialog
        modal: true
        anchors.centerIn: parent
        width: 460
        background: Rectangle { color: B.card; radius: 14; border.color: B.border }
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: tt("overwrite_title"); color: B.fg; font.pixelSize: 15; font.weight: Font.DemiBold }
            Text { id: overwriteNames; Layout.fillWidth: true; color: B.fg2; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Item { Layout.fillWidth: true }
                AppButton { label: tt("ico_too_large_cancel"); onActivated: { overwriteDialog.close(); B.overwriteAnswer(false) } }
                AppButton { label: tt("ico_too_large_ok"); filled: true; onActivated: { overwriteDialog.close(); B.overwriteAnswer(true) } }
            }
        }
        function show(names) { overwriteNames.text = B.overwriteText(names); open() }
    }
    Connections {
        target: B
        function onAskOverwrite(names) { overwriteDialog.show(names) }
    }

    // ── каркас ─────────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Заголовок
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 56; color: B.bg
            Hairline { anchors.bottom: parent.bottom; width: parent.width }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 16; spacing: 10
                Text { text: "⬡"; color: B.accent; font.pixelSize: 22 }
                Text { text: "Formatix"; color: B.fg; font.pixelSize: 17; font.weight: Font.DemiBold }
                Text { text: "v" + B.version; color: B.fg3; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                AppButton { label: tt("settings_title"); onActivated: { settingsSheet.openSheet() } }
                Text {
                    text: "♥"; color: B.fg3; font.pixelSize: 18
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: parent.color = B.red
                        onExited: parent.color = B.fg3
                        onClicked: Qt.openUrlExternally("https://github.com/cyber-anderson/Formatix#%EF%B8%8F-support-the-project")
                    }
                }
            }
        }

        // Панель инструментов
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20; Layout.topMargin: 14
            spacing: 10
            AppButton { label: tt("add"); filled: true; onActivated: { fileDialog.open() } }
            AppButton { label: tt("clear"); onActivated: { B.clearFiles() } }
            Item { Layout.fillWidth: true }
            Text {
                text: B.filesCount > 0
                      ? tt("files_count").replace("{n}", B.filesCount) + "   ·   " + B.srcBytes
                      : ""
                color: B.fg2; font.pixelSize: 12
            }
        }

        // Основная область: два списка
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.leftMargin: 20; Layout.rightMargin: 20; Layout.topMargin: 12
            spacing: 14

            // Исходные файлы
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 8
                    RowLayout { spacing: 8
                        Text { text: "📂"; font.pixelSize: 14 }
                        Text { text: tt("src_panel").replace("📂  ", ""); color: B.fg; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                    Hairline { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true; Layout.fillHeight: true
                        ListView {
                            id: srcList
                            anchors.fill: parent
                            model: B.filesModel
                            spacing: 2
                            clip: true
                            delegate: RowLayout {
                                width: srcList.width
                                height: 30
                                Text { text: "✕"; color: B.fg3; font.pixelSize: 11
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: B.removeFile(index) } }
                                Text { Layout.fillWidth: true; text: model.name; color: B.fg; font.pixelSize: 13; elide: Text.ElideMiddle }
                                Text { text: model.res; color: B.fg2; font.pixelSize: 12; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                                Text { text: model.size; color: B.fg2; font.pixelSize: 12; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                            }
                        }
                        // Пустое состояние
                        Column {
                            anchors.centerIn: parent; spacing: 10; visible: B.filesCount === 0
                            Text { text: "⬇"; color: B.fg3; font.pixelSize: 30; anchors.horizontalCenter: parent.horizontalCenter }
                            Text { text: tt("drop_hint"); color: B.fg2; font.pixelSize: 13;
                                   horizontalAlignment: Text.AlignHCenter; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                        DropArea {
                            anchors.fill: parent
                            onDropped: function(drop) { if (drop.hasUrls) B.addFiles(drop.urls) }
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: B.filesCount === 0
                            cursorShape: Qt.PointingHandCursor
                            onClicked: fileDialog.open()
                        }
                    }
                    Text { text: tt("was") + " " + B.srcBytes; color: B.fg2; font.pixelSize: 12; visible: B.filesCount > 0 }
                }
            }

            // Результат
            Card {
                Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 8
                    RowLayout { spacing: 8
                        Text { text: "✅"; font.pixelSize: 14 }
                        Text { text: tt("dst_panel").replace("✅  ", ""); color: B.fg; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                    Hairline { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true; Layout.fillHeight: true
                        ListView {
                            id: resList
                            anchors.fill: parent
                            model: B.resultsModel
                            spacing: 2
                            clip: true
                            delegate: RowLayout {
                                width: resList.width
                                height: 30
                                Text { text: model.ok ? "✔" : "✘"; color: model.ok ? B.green : B.red; font.pixelSize: 12 }
                                Text { Layout.fillWidth: true; text: model.name; color: B.fg; font.pixelSize: 13; elide: Text.ElideMiddle }
                                Text { text: model.res; color: B.fg2; font.pixelSize: 12; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                                Text { text: model.size; color: B.fg2; font.pixelSize: 12; Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight }
                            }
                        }
                        Text { visible: B.filesCount > 0 && resList.count === 0
                               anchors.centerIn: parent; text: tt("ready"); color: B.fg3; font.pixelSize: 13 }
                    }
                    RowLayout { visible: B.filesCount > 0; spacing: 8
                        Text { text: tt("became"); color: B.fg2; font.pixelSize: 12 }
                        Text { text: B.dstBytes; color: B.green; font.pixelSize: 12; font.weight: Font.DemiBold }
                        Item { Layout.fillWidth: true }
                        Text { text: "📂"; font.pixelSize: 13
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: B.openOutFolder() } }
                    }
                }
            }
        }

        // Нижняя панель управления
        Card {
            Layout.fillWidth: true
            Layout.leftMargin: 20; Layout.rightMargin: 20; Layout.bottomMargin: 16; Layout.topMargin: 12
            implicitHeight: 148
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10

                // Папка сохранения
                RowLayout { Layout.fillWidth: true; spacing: 10
                    SectionLabel { text: tt("save_folder") }
                    Rectangle {
                        Layout.fillWidth: true; implicitHeight: 30; radius: 8
                        color: B.bg2; border.color: B.border; border.width: 1
                        Text {
                            anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                            text: B.outDirDisplay; color: B.outDir === "" ? B.fg3 : B.fg
                            font.pixelSize: 12; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter
                        }
                    }
                    AppButton { label: tt("pick_dir"); onActivated: { folderDialog.open() } }
                    AppButton { label: "✕"; onActivated: { B.outDir = "" } }
                }

                // Формат · Качество · Разрешение · Конвертировать
                RowLayout { Layout.fillWidth: true; spacing: 18

                    ColumnLayout { spacing: 6
                        SectionLabel { text: tt("format_lbl") }
                        AppCombo {
                            id: fmtCombo
                            model: B.formats()
                            implicitWidth: 110
                            Component.onCompleted: currentIndex = find(B.fmt)
                            onActivated: function(i) { B.fmt = currentText }
                        }
                    }

                    ColumnLayout { spacing: 6
                        RowLayout { spacing: 8
                            SectionLabel { text: tt("quality_lbl") }
                            TogglePill {
                                options: [["percent", tt("qmode_percent")], ["size", tt("qmode_size")]]
                                value: B.qualityMode
                                onPicked: function(v) { B.qualityMode = v }
                            }
                        }
                        RowLayout { spacing: 8; visible: B.qualityMode === "percent"
                            Slider {
                                id: qualSlider
                                from: 10; to: 99
                                implicitWidth: 190
                                value: B.quality
                                onMoved: B.quality = value
                                background: Rectangle {
                                    x: qualSlider.leftPadding; y: qualSlider.topPadding + qualSlider.availableHeight / 2 - 3
                                    width: qualSlider.availableWidth; height: 6; radius: 3; color: B.bg3
                                    Rectangle {
                                        width: qualSlider.visualPosition * parent.width; height: parent.height
                                        radius: 3; color: B.accent
                                    }
                                }
                                handle: Rectangle {
                                    x: qualSlider.leftPadding + qualSlider.visualPosition * (qualSlider.availableWidth - width)
                                    y: qualSlider.topPadding + qualSlider.availableHeight / 2 - height / 2
                                    width: 18; height: 18; radius: 9
                                    color: "#fff"; border.color: B.accent; border.width: 2
                                }
                            }
                            Rectangle {
                                implicitWidth: 44; implicitHeight: 26; radius: 8; color: B.accent
                                TextInput {
                                    anchors.centerIn: parent; text: B.quality; color: "#fff"
                                    font.pixelSize: 13; font.weight: Font.DemiBold
                                    horizontalAlignment: TextInput.AlignHCenter; width: 36
                                    onEditingFinished: {
                                        var v = parseInt(text)
                                        if (!isNaN(v)) B.quality = v
                                        text = B.quality
                                    }
                                }
                            }
                        }
                        RowLayout { spacing: 8; visible: B.qualityMode === "size"
                            Rectangle {
                                implicitWidth: 64; implicitHeight: 26; radius: 8; color: B.accent
                                TextInput {
                                    anchors.centerIn: parent; text: B.targetSizeVal; color: "#fff"
                                    font.pixelSize: 13; font.weight: Font.DemiBold
                                    horizontalAlignment: TextInput.AlignHCenter
                                    onEditingFinished: B.targetSizeVal = text
                                }
                            }
                            AppCombo {
                                id: unitCombo
                                model: ["KB", "MB"]
                                implicitWidth: 78
                                Component.onCompleted: currentIndex = find(B.targetUnit)
                                onActivated: function(i) { B.setTargetUnit(currentText) }
                            }
                        }
                    }

                    ColumnLayout { spacing: 6
                        SectionLabel { text: tt("resize_lbl") }
                        RowLayout { spacing: 8
                            AppCombo {
                                id: resCombo
                                implicitWidth: 210
                                model: B.resizeModes()
                                displayText: model !== undefined && currentIndex >= 0 ? model[currentIndex][0] : ""
                                delegate: ItemDelegate {
                                    width: resCombo.width
                                    contentItem: Text { text: modelData[0]; color: B.fg; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
                                    highlighted: resCombo.highlightedIndex === index
                                    background: Rectangle { color: highlighted ? B.tint : "transparent"; radius: 6 }
                                }
                                Component.onCompleted: {
                                    for (var i = 0; i < model.length; i++)
                                        if (model[i][1] === B.resizeModeKey) currentIndex = i
                                }
                                onActivated: function(i) { B.resizeModeKey = model[i][1] }
                            }
                            Rectangle {
                                visible: B.resizeModeKey !== "no_change"
                                implicitWidth: 56; implicitHeight: 30; radius: 8
                                color: B.card; border.color: B.border; border.width: 1
                                TextInput {
                                    anchors.centerIn: parent; text: B.wVal === "" ? "—" : B.wVal
                                    color: B.fg; font.pixelSize: 13; horizontalAlignment: TextInput.AlignHCenter
                                    onEditingFinished: { if (text !== "—") B.wVal = text; text = B.wVal === "" ? "—" : B.wVal }
                                }
                            }
                            Text { text: "×"; color: B.fg3; visible: B.resizeModeKey !== "no_change" }
                            Rectangle {
                                visible: B.resizeModeKey !== "no_change"
                                implicitWidth: 56; implicitHeight: 30; radius: 8
                                color: B.card; border.color: B.border; border.width: 1
                                TextInput {
                                    anchors.centerIn: parent; text: B.hVal === "" ? "—" : B.hVal
                                    color: B.fg; font.pixelSize: 13; horizontalAlignment: TextInput.AlignHCenter
                                    onEditingFinished: { if (text !== "—") B.hVal = text; text = B.hVal === "" ? "—" : B.hVal }
                                }
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    AppButton {
                        id: convertBtn
                        label: B.running ? tt("stop_btn") : tt("convert_btn")
                        filled: true; big: true
                        onActivated: { B.running ? B.stopConvert() : B.convert() }
                    }
                }

                // Прогресс и статус
                RowLayout { Layout.fillWidth: true; spacing: 12
                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0; to: 100; value: B.progress
                        indeterminate: B.running && B.progress === 0
                        background: Rectangle {
                            implicitHeight: 6; radius: 3; color: B.bg3
                            Rectangle { width: parent.width * (B.progress / 100); height: parent.height; radius: 3; color: B.accent }
                        }
                        contentItem: Item { implicitHeight: 6 }
                    }
                    Text { text: B.status; color: B.fg2; font.pixelSize: 12; Layout.preferredWidth: 260; elide: Text.ElideRight }
                    Text { text: B.statusErr; color: B.red; font.pixelSize: 12; visible: B.statusErr !== ""; Layout.maximumWidth: 260; elide: Text.ElideRight }
                }
            }
        }
    }

    // ── окно настроек ───────────────────────────────────────────────────────────
    Popup {
        id: settingsSheet
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: 420; height: Math.min(660, win.height - 60)
        modal: true; focus: true
        background: Rectangle { color: B.bg; radius: 16; border.color: B.border }
        function openSheet() { open() }

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 14

            Text { text: tt("settings_title"); color: B.fg; font.pixelSize: 18; font.weight: Font.DemiBold
                   Layout.alignment: Qt.AlignHCenter }

            // Язык
            RowLayout { Layout.fillWidth: true; spacing: 10
                Text { text: tt("settings_lang"); color: B.fg; font.pixelSize: 13 }
                Item { Layout.fillWidth: true }
                AppCombo {
                    implicitWidth: 150
                    model: B.langNames()
                    Component.onCompleted: currentIndex = find(B.langName())
                    onActivated: function(i) { B.setLangByName(currentText) }
                }
            }
            // Тема (смена живая)
            RowLayout { Layout.fillWidth: true; spacing: 10
                Text { text: tt("settings_theme"); color: B.fg; font.pixelSize: 13 }
                Item { Layout.fillWidth: true }
                TogglePill {
                    options: [["dark", tt("theme_dark")], ["light", tt("theme_light")]]
                    value: B.themeName
                    onPicked: function(v) { B.setTheme(v) }
                }
            }
            CheckRow {
                label: tt("settings_delete_original")
                checked: B.deleteOriginal
                onToggled: B.deleteOriginal = !B.deleteOriginal
            }
            Hairline { Layout.fillWidth: true }

            // Имя файла
            SectionLabel { text: tt("settings_filename_lbl") }
            AppCombo {
                id: fnCombo
                Layout.fillWidth: true
                model: [[tt("fn_preset_original"), "original"], [tt("fn_preset_number"), "number"],
                        [tt("fn_preset_date"), "date"], [tt("fn_preset_custom"), "custom"]]
                displayText: model !== undefined && currentIndex >= 0 ? model[currentIndex][0] : ""
                delegate: ItemDelegate {
                    width: fnCombo.width
                    contentItem: Text { text: modelData[0]; color: B.fg; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
                    highlighted: fnCombo.highlightedIndex === index
                    background: Rectangle { color: highlighted ? B.tint : "transparent"; radius: 6 }
                }
                Component.onCompleted: {
                    for (var i = 0; i < model.length; i++)
                        if (model[i][1] === B.fnPreset) currentIndex = i
                }
                onActivated: function(i) { B.fnPreset = model[i][1] }
            }
            // Конструктор шаблона — только для «custom»
            Flow {
                visible: B.fnPreset === "custom"
                Layout.fillWidth: true; spacing: 6
                AppButton { label: tt("fn_add_name"); onActivated: { B.addToken("name") } }
                AppButton { label: tt("fn_add_index"); onActivated: { B.addToken("index") } }
                AppButton { label: tt("fn_add_date"); onActivated: { B.addToken("date") } }
                AppButton { label: tt("fn_add_text"); onActivated: { textPrompt.open() } }
            }
            Flow {
                visible: B.fnPreset === "custom"
                Layout.fillWidth: true; spacing: 6
                Repeater {
                    model: B.tokens
                    delegate: Rectangle {
                        required property var modelData
                        property int tindex: index
                        radius: 9; implicitHeight: 24; width: chipLbl.implicitWidth + 30
                        color: modelData.type === "name" ? B.accent : (modelData.type === "index" ? B.accentHover : B.bg3)
                        Text { id: chipLbl; anchors.centerIn: parent
                               text: (modelData.type === "text" ? modelData.value : tt("fn_add_" + modelData.type)) + " ✕"
                               color: modelData.type === "date" ? B.fg : "#fff"; font.pixelSize: 11 }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: B.removeToken(parent.tindex) }
                    }
                }
            }
            RowLayout { visible: B.fnPreset === "custom"; Layout.fillWidth: true; spacing: 8
                Text { text: tt("fn_preview_lbl"); color: B.fg3; font.pixelSize: 11 }
                Text { text: B.namePreview(); color: B.fg; font.pixelSize: 12; font.family: "Inter" }
            }

            Hairline { Layout.fillWidth: true }

            // Обновления
            RowLayout { Layout.fillWidth: true; spacing: 10
                Text { text: tt("update_check_now"); color: B.accent; font.pixelSize: 13
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: B.checkUpdatesNow() } }
                Item { Layout.fillWidth: true }
                Text {
                    text: B.updateState; color: B.fg2; font.pixelSize: 12
                    MouseArea { anchors.fill: parent; enabled: parent.text.indexOf("→") > 0
                                cursorShape: Qt.PointingHandCursor; onClicked: B.openUpdateUrl() }
                }
            }

            Item { Layout.fillHeight: true }
            AppButton { label: "✕"; Layout.alignment: Qt.AlignHCenter
                        onActivated: { settingsSheet.close() } }
        }
    }

    Dialog {
        id: textPrompt
        modal: true; anchors.centerIn: parent; width: 360
        title: tt("fn_custom_text_prompt")
        background: Rectangle { color: B.card; radius: 14; border.color: B.border }
        contentItem: ColumnLayout { spacing: 10
            TextInput { id: promptInput; color: B.fg; font.pixelSize: 13
                Rectangle { anchors.fill: parent; anchors.margins: -6; color: B.bg2; radius: 8; z: -1 } }
        }
        footer: RowLayout {
            Item { Layout.fillWidth: true }
            AppButton { label: tt("ico_too_large_cancel"); onActivated: { textPrompt.close() } }
            AppButton { label: tt("ico_too_large_ok"); filled: true
                        onActivated: { B.addTextToken(promptInput.text); promptInput.text = ""; textPrompt.close() } }
        }
        onAboutToShow: promptInput.forceActiveFocus()
    }
}
