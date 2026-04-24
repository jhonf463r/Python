import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * ContextualSuggestionsPanel — panel de sugerencias contextuales para el chat.
 *
 * Muestra sugerencias de acciones basadas en el estado actual del sistema:
 *   - Sugerencias de comandos disponibles
 *   - Acciones rapidas basadas en contexto
 *   - Hints de capacidades no exploradas
 *   - Atajos inteligentes adaptados al historial
 *
 * Properties:
 *   suggestions: list — [{text, category, icon, action, priority}]
 *   visible: bool — controla visibilidad del panel
 *   maxVisible: int — maximo de sugerencias a mostrar (default 4)
 *
 * Signals:
 *   suggestionClicked(string action, string text)
 *   dismissed()
 */
Rectangle {
    id: suggestionsPanel
    width: parent ? parent.width : 400
    height: visible ? Math.min(suggestionsCol.implicitHeight + 16, maxHeight) : 0
    radius: 10
    color: "#141e28"
    border.width: 1
    border.color: "#2a3a4a"
    clip: true
    visible: (suggestions || []).length > 0

    readonly property int maxHeight: 180
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color accentColor: "#4fc3f7"
    readonly property color successColor: "#81c784"

    property var suggestions: []
    property int maxVisible: 4

    signal suggestionClicked(string action, string text)
    signal dismissed()

    Behavior on height {
        NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
    }

    Column {
        id: suggestionsCol
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        // Header
        RowLayout {
            width: suggestionsCol.width
            spacing: 6

            Label {
                text: "\u2728"
                font.pixelSize: 11
            }

            Label {
                text: "Sugerencias"
                color: textSecondary
                font.pixelSize: 10
                font.family: "Segoe UI"
                font.bold: true
                Layout.fillWidth: true
            }

            // Dismiss button
            Rectangle {
                width: 18; height: 18; radius: 9
                color: dismissMa.containsMouse ? "#2a3a4a" : "transparent"

                Label {
                    anchors.centerIn: parent
                    text: "\u2715"
                    color: textSecondary
                    font.pixelSize: 8
                }

                MouseArea {
                    id: dismissMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: suggestionsPanel.dismissed()
                }
            }
        }

        // Suggestion items
        Repeater {
            model: {
                var sorted = (suggestionsPanel.suggestions || []).slice()
                sorted.sort(function(a, b) { return (b.priority || 0) - (a.priority || 0) })
                return sorted.slice(0, suggestionsPanel.maxVisible)
            }

            delegate: Rectangle {
                width: suggestionsCol.width
                height: suggRow.implicitHeight + 10
                radius: 6
                color: suggItemMa.containsMouse ? "#1a2e3e" : "transparent"
                border.width: suggItemMa.containsMouse ? 1 : 0
                border.color: "#2a3a4a"

                RowLayout {
                    id: suggRow
                    anchors.fill: parent
                    anchors.margins: 5
                    spacing: 6

                    // Category color indicator
                    Rectangle {
                        width: 3
                        Layout.preferredHeight: parent.height - 4
                        radius: 2
                        color: {
                            var cat = modelData.category || "general"
                            if (cat === "command") return accentColor
                            if (cat === "diagnostic") return "#ffb74d"
                            if (cat === "evolution") return "#ce93d8"
                            if (cat === "audit") return successColor
                            if (cat === "learning") return "#90caf9"
                            return textSecondary
                        }
                    }

                    // Icon
                    Label {
                        text: modelData.icon || "\u25b8"
                        font.pixelSize: 12
                        visible: (modelData.icon || "") !== ""
                    }

                    // Suggestion text
                    Column {
                        Layout.fillWidth: true
                        spacing: 1

                        Label {
                            text: modelData.text || ""
                            color: textPrimary
                            font.pixelSize: 11
                            font.family: "Segoe UI"
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Label {
                            visible: (modelData.category || "") !== ""
                            text: modelData.category || ""
                            color: "#5a6570"
                            font.pixelSize: 9
                            font.family: "Segoe UI"
                            font.capitalization: Font.AllUppercase
                        }
                    }

                    // Arrow
                    Label {
                        text: "\u2192"
                        color: accentColor
                        font.pixelSize: 10
                        visible: suggItemMa.containsMouse
                    }
                }

                MouseArea {
                    id: suggItemMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: suggestionsPanel.suggestionClicked(modelData.action || "", modelData.text || "")
                }
            }
        }
    }
}
