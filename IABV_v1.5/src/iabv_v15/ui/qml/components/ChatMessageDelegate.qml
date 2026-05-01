import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * ChatMessageDelegate — delegado avanzado para mensajes del chat.
 *
 * Cada mensaje puede tener:
 *   - Texto principal con soporte de bloques de codigo
 *   - Botones de accion contextuales (copiar, descargar, ejecutar, aplicar)
 *   - Indicador de estado (thinking, complete, error)
 *   - Adjuntos con preview
 *   - Metadata expandible (modelo usado, tiempo, tokens)
 *   - Razonamiento colapsable (thinking trace)
 *   - Acciones inline (copiar respuesta, descargar, aplicar)
 *
 * Data model (modelData):
 *   role: "user" | "system" | "assistant"
 *   speaker: string
 *   text: string
 *   meta: string (optional)
 *   status: "complete" | "thinking" | "error" (optional)
 *   actions: [{label, action, icon}] (optional)
 *   codeBlocks: [{language, code, canApply}] (optional)
 *   attachments: [{name, type, size, path}] (optional)
 *   timestamp: string (optional)
 *   reasoning: string (optional — trace de razonamiento colapsable)
 *   tokenCount: int (optional)
 *   modelUsed: string (optional)
 *   elapsed: string (optional — ej: "2.3s")
 *   liveStatus: string (optional — "streaming" | "routing" | "queued")
 *   evidenceTag: string (optional — "observed" | "inferred" | "unresolved")
 */
Rectangle {
    id: msgDelegate
    width: parent ? parent.width : 400
    radius: 14
    color: {
        if (modelData.role === "user") return "#26414b"
        if (modelData.status === "error") return "#2a1a1a"
        return "#22303a"
    }
    border.width: 1
    border.color: {
        if (modelData.status === "error") return "#6e3030"
        if (modelData.status === "thinking") return "#3d6e5c"
        return "#42505d"
    }
    implicitHeight: contentCol.implicitHeight + 20

    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color accentColor: "#4fc3f7"
    readonly property color successColor: "#81c784"
    readonly property color warningColor: "#ffb74d"

    signal actionRequested(string actionId, var actionData)
    signal copyRequested(string text)
    signal downloadRequested(string text, string filename)
    signal applyCodeRequested(string code, string language)
    signal attachmentClicked(string path, string name)

    Column {
        id: contentCol
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        // === Header: speaker + timestamp + status + live indicator ===
        RowLayout {
            width: contentCol.width
            spacing: 8

            // Status indicator dot
            Rectangle {
                width: 8; height: 8; radius: 4
                visible: modelData.status !== undefined && modelData.status !== "complete"
                color: {
                    if (modelData.status === "thinking") return "#4fc3f7"
                    if (modelData.status === "error") return "#cf7e7e"
                    if (modelData.liveStatus === "streaming") return successColor
                    if (modelData.liveStatus === "routing") return warningColor
                    return "transparent"
                }

                SequentialAnimation on opacity {
                    running: modelData.status === "thinking" || modelData.liveStatus === "streaming"
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.3; duration: 800 }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 800 }
                }
            }

            Label {
                text: modelData.speaker || (modelData.role === "user" ? "Tu" : "IABV")
                color: modelData.role === "user" ? "#7ec8e3" : accentColor
                font.pixelSize: 13
                font.family: "Segoe UI"
                font.bold: true
                Layout.fillWidth: true
            }

            // Live status badge
            Rectangle {
                visible: (modelData.liveStatus || "") !== ""
                width: liveLabel.implicitWidth + 10
                height: 16
                radius: 8
                color: {
                    if (modelData.liveStatus === "streaming") return "#1b3d2a"
                    if (modelData.liveStatus === "routing") return "#3d3520"
                    if (modelData.liveStatus === "queued") return "#1a2a3a"
                    return "transparent"
                }
                Label {
                    id: liveLabel
                    anchors.centerIn: parent
                    text: modelData.liveStatus || ""
                    color: {
                        if (modelData.liveStatus === "streaming") return successColor
                        if (modelData.liveStatus === "routing") return warningColor
                        return textSecondary
                    }
                    font.pixelSize: 9
                    font.family: "Segoe UI"
                    font.capitalization: Font.AllUppercase
                }
            }

            Label {
                text: modelData.timestamp || ""
                visible: text.length > 0
                color: textSecondary
                font.pixelSize: 10
                font.family: "Segoe UI"
            }
        }

        // === Main text content ===
        TextEdit {
            width: contentCol.width
            text: modelData.text || ""
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            textFormat: TextEdit.PlainText
            color: textPrimary
            font.family: "Segoe UI"
            font.pixelSize: 12
            height: Math.max(contentHeight, 18)
        }

        // === Code blocks ===
        Repeater {
            model: modelData.codeBlocks || []
            delegate: Rectangle {
                width: contentCol.width
                radius: 8
                color: "#0d1117"
                border.width: 1
                border.color: "#30363d"
                implicitHeight: codeCol.implicitHeight + 12

                Column {
                    id: codeCol
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    RowLayout {
                        width: codeCol.width
                        spacing: 6

                        Label {
                            text: modelData.language || "code"
                            color: "#8b949e"
                            font.pixelSize: 10
                            font.family: "Consolas"
                            Layout.fillWidth: true
                        }

                        // Copy button
                        Rectangle {
                            width: codeCopyLabel.implicitWidth + 12
                            height: 20
                            radius: 4
                            color: codeCopyMa.containsMouse ? "#30363d" : "transparent"
                            property bool copied: false
                            Label {
                                id: codeCopyLabel
                                anchors.centerIn: parent
                                text: parent.copied ? "Copiado!" : "Copiar"
                                color: parent.copied ? successColor : textSecondary
                                font.pixelSize: 10
                                font.family: "Segoe UI"
                            }
                            MouseArea {
                                id: codeCopyMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    parent.copied = true
                                    msgDelegate.copyRequested(modelData.code)
                                    codeCopyTimer.start()
                                }
                            }
                            Timer {
                                id: codeCopyTimer
                                interval: 2000
                                onTriggered: parent.copied = false
                            }
                        }

                        // Apply button (visible only when canApply)
                        Rectangle {
                            visible: modelData.canApply === true
                            width: applyLabel.implicitWidth + 12
                            height: 20
                            radius: 4
                            color: applyMa.containsMouse ? "#1a3a2a" : "transparent"
                            border.width: 1
                            border.color: applyMa.containsMouse ? successColor : "#30363d"
                            Label {
                                id: applyLabel
                                anchors.centerIn: parent
                                text: "Aplicar"
                                color: successColor
                                font.pixelSize: 10
                                font.family: "Segoe UI"
                                font.bold: true
                            }
                            MouseArea {
                                id: applyMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: msgDelegate.applyCodeRequested(modelData.code, modelData.language)
                            }
                        }
                    }

                    // Code content
                    TextEdit {
                        width: codeCol.width
                        text: modelData.code || ""
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        textFormat: TextEdit.PlainText
                        color: "#e6edf3"
                        font.family: "Consolas"
                        font.pixelSize: 11
                        height: Math.min(contentHeight, 300)
                        clip: true
                    }
                }
            }
        }

        // === Attachments ===
        Repeater {
            model: modelData.attachments || []
            delegate: Rectangle {
                width: contentCol.width
                height: 36
                radius: 6
                color: attachFileMa.containsMouse ? "#2a3a4a" : "#1a2a3a"
                border.width: 1
                border.color: "#2a3a4a"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 6

                    Label {
                        text: {
                            var ext = (modelData.name || "").split('.').pop().toLowerCase()
                            if (["png","jpg","jpeg","gif","svg","bmp"].indexOf(ext) >= 0) return "\ud83d\uddbc"
                            if (["pdf"].indexOf(ext) >= 0) return "\ud83d\udcc4"
                            if (["py","js","ts","qml","cpp","rs"].indexOf(ext) >= 0) return "\ud83d\udcbb"
                            if (["zip","tar","gz","7z"].indexOf(ext) >= 0) return "\ud83d\udce6"
                            return "\ud83d\udcce"
                        }
                        font.pixelSize: 16
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 1
                        Label {
                            text: modelData.name || "archivo"
                            color: accentColor
                            font.pixelSize: 11
                            font.family: "Segoe UI"
                            elide: Text.ElideMiddle
                            width: parent.width
                        }
                        Label {
                            text: {
                                var s = modelData.size || 0
                                if (s < 1024) return s + " B"
                                if (s < 1048576) return (s/1024).toFixed(1) + " KB"
                                return (s/1048576).toFixed(1) + " MB"
                            }
                            color: textSecondary
                            font.pixelSize: 9
                            font.family: "Segoe UI"
                        }
                    }
                }

                MouseArea {
                    id: attachFileMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: msgDelegate.attachmentClicked(modelData.path, modelData.name)
                }
            }
        }

        // === Reasoning trace (collapsible) ===
        Column {
            visible: (modelData.reasoning || "") !== ""
            width: contentCol.width
            spacing: 2

            Rectangle {
                width: parent.width
                height: reasoningHeader.implicitHeight + 8
                radius: 6
                color: reasoningMa.containsMouse ? "#1a2a3a" : "transparent"

                RowLayout {
                    id: reasoningHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 4
                    spacing: 4

                    Label {
                        text: reasoningExpanded.visible ? "\u25bc" : "\u25b6"
                        color: textSecondary
                        font.pixelSize: 8
                    }
                    Label {
                        text: "Razonamiento"
                        color: textSecondary
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                        font.italic: true
                        Layout.fillWidth: true
                    }
                }

                MouseArea {
                    id: reasoningMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    property bool expanded: false
                    onClicked: expanded = !expanded
                }
            }

            TextEdit {
                id: reasoningExpanded
                visible: reasoningMa.expanded
                width: contentCol.width
                text: modelData.reasoning || ""
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                color: "#9da5b0"
                font.family: "Segoe UI"
                font.pixelSize: 11
                font.italic: true
                height: Math.min(contentHeight, 200)
                clip: true
            }
        }

        // === Action buttons row ===
        Flow {
            width: contentCol.width
            spacing: 6
            visible: (modelData.role === "assistant" && modelData.status !== "thinking") || (modelData.actions || []).length > 0

            // Copy response button
            Rectangle {
                visible: modelData.role === "assistant"
                width: copyRespLabel.implicitWidth + 14
                height: 24
                radius: 6
                color: copyRespMa.containsMouse ? "#2a3a4a" : "transparent"
                border.width: 1
                border.color: "#2a3a4a"
                property bool copied: false

                Label {
                    id: copyRespLabel
                    anchors.centerIn: parent
                    text: parent.copied ? "\u2713 Copiado" : "Copiar respuesta"
                    color: parent.copied ? successColor : textSecondary
                    font.pixelSize: 10
                    font.family: "Segoe UI"
                }
                MouseArea {
                    id: copyRespMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        parent.copied = true
                        msgDelegate.copyRequested(modelData.text)
                        copyRespTimer.start()
                    }
                }
                Timer {
                    id: copyRespTimer
                    interval: 2000
                    onTriggered: parent.copied = false
                }
            }

            // Download response button
            Rectangle {
                visible: modelData.role === "assistant" && (modelData.text || "").length > 100
                width: dlLabel.implicitWidth + 14
                height: 24
                radius: 6
                color: dlMa.containsMouse ? "#2a3a4a" : "transparent"
                border.width: 1
                border.color: "#2a3a4a"

                Label {
                    id: dlLabel
                    anchors.centerIn: parent
                    text: "Descargar"
                    color: textSecondary
                    font.pixelSize: 10
                    font.family: "Segoe UI"
                }
                MouseArea {
                    id: dlMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: msgDelegate.downloadRequested(modelData.text, "respuesta_iabv.txt")
                }
            }

            // Custom action buttons
            Repeater {
                model: modelData.actions || []
                delegate: Rectangle {
                    width: actLabel.implicitWidth + 14
                    height: 24
                    radius: 6
                    color: actMa.containsMouse ? "#2a3a4a" : "transparent"
                    border.width: 1
                    border.color: "#2a3a4a"

                    Label {
                        id: actLabel
                        anchors.centerIn: parent
                        text: modelData.label
                        color: accentColor
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                    }
                    MouseArea {
                        id: actMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: msgDelegate.actionRequested(modelData.action, modelData)
                    }
                }
            }
        }

        // === Metadata footer (model, tokens, time, evidence tag) ===
        RowLayout {
            width: contentCol.width
            spacing: 8
            visible: (modelData.modelUsed || "") !== "" || (modelData.tokenCount || 0) > 0 || (modelData.meta || "") !== "" || (modelData.evidenceTag || "") !== ""

            // Evidence tag badge (observed / inferred / unresolved)
            Rectangle {
                visible: (modelData.evidenceTag || "") !== ""
                width: evidenceLabel.implicitWidth + 10
                height: 16
                radius: 8
                color: {
                    if (modelData.evidenceTag === "observed") return "#1b3d2a"
                    if (modelData.evidenceTag === "inferred") return "#1a2a3a"
                    if (modelData.evidenceTag === "unresolved") return "#3d3520"
                    return "transparent"
                }
                border.width: 1
                border.color: {
                    if (modelData.evidenceTag === "observed") return "#2e6e47"
                    if (modelData.evidenceTag === "inferred") return "#2e4a6e"
                    if (modelData.evidenceTag === "unresolved") return "#6e5a2e"
                    return "transparent"
                }
                Label {
                    id: evidenceLabel
                    anchors.centerIn: parent
                    text: {
                        if (modelData.evidenceTag === "observed") return "observado"
                        if (modelData.evidenceTag === "inferred") return "inferido"
                        if (modelData.evidenceTag === "unresolved") return "sin confirmar"
                        return ""
                    }
                    color: {
                        if (modelData.evidenceTag === "observed") return "#81c784"
                        if (modelData.evidenceTag === "inferred") return "#4fc3f7"
                        if (modelData.evidenceTag === "unresolved") return "#ffb74d"
                        return "#6a7580"
                    }
                    font.pixelSize: 9
                    font.family: "Segoe UI"
                    font.capitalization: Font.AllUppercase
                }
            }

            Label {
                text: modelData.meta || ""
                visible: (modelData.meta || "") !== ""
                color: "#6a7580"
                font.pixelSize: 9
                font.family: "Segoe UI"
                font.italic: true
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: modelData.modelUsed || ""
                visible: (modelData.modelUsed || "") !== ""
                color: "#6a7580"
                font.pixelSize: 9
                font.family: "Consolas"
            }

            Label {
                text: (modelData.tokenCount || 0) > 0 ? (modelData.tokenCount + " tok") : ""
                visible: (modelData.tokenCount || 0) > 0
                color: "#6a7580"
                font.pixelSize: 9
                font.family: "Segoe UI"
            }

            Label {
                text: modelData.elapsed || ""
                visible: (modelData.elapsed || "") !== ""
                color: "#6a7580"
                font.pixelSize: 9
                font.family: "Segoe UI"
            }
        }
    }
}
