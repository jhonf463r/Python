import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * ChatToolbar — barra de herramientas avanzada sobre el area de input del chat.
 *
 * Muestra:
 *   - Boton de adjuntar archivos (con estado de archivos pendientes)
 *   - Boton de modo codigo (toggle para enviar codigo)
 *   - Indicador de herramientas activas
 *   - Selector de contexto (que proveedor usar para la respuesta)
 *   - Boton de buscar en historial
 *   - Boton de ingresar clave API
 *   - Indicador de estado en vivo del sistema
 *
 * Properties:
 *   toolCount: int — herramientas disponibles
 *   activeProvider: string — proveedor activo
 *   codeMode: bool — si esta en modo codigo
 *   canAttach: bool — si adjuntar esta habilitado
 *   attachedCount: int — archivos adjuntos pendientes
 *   systemStatus: string — "idle" | "processing" | "error"
 *   searchQuery: string — texto de busqueda activo
 *
 * Signals:
 *   attachClicked()
 *   codeModeToggled()
 *   searchClicked()
 *   providerSwitchClicked()
 *   keyInputRequested()
 *   clearAttachments()
 *   searchQueryChanged(string query)
 */
Rectangle {
    id: toolbar
    width: parent ? parent.width : 400
    height: searchBar.visible ? 72 : 36
    radius: 8
    color: "#162028"
    border.width: 1
    border.color: "#2a3a4a"

    property int toolCount: 0
    property string activeProvider: "auto"
    property bool codeMode: false
    property bool canAttach: true
    property int attachedCount: 0
    property string systemStatus: "idle"
    property string searchQuery: ""

    signal attachClicked()
    signal codeModeToggled()
    signal searchClicked()
    signal providerSwitchClicked()
    signal keyInputRequested()
    signal clearAttachments()

    readonly property color textSecondary: "#d1d8df"
    readonly property color accentColor: "#4fc3f7"
    readonly property color successColor: "#81c784"
    readonly property color warningColor: "#ffb74d"
    readonly property color errorColor: "#cf7e7e"

    Column {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            width: parent.width
            height: 36
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 4

            Item { width: 4 }

            // Attach button with badge
            ToolButton {
                id: attachBtn
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                enabled: toolbar.canAttach
                opacity: enabled ? 1.0 : 0.4

                background: Rectangle {
                    radius: 6
                    color: attachBtn.hovered ? "#2a3a4a" : "transparent"
                }

                contentItem: Item {
                    Label {
                        anchors.centerIn: parent
                        text: "\ud83d\udcce"
                        font.pixelSize: 14
                    }
                    // Badge for attached files count
                    Rectangle {
                        visible: toolbar.attachedCount > 0
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.topMargin: -2
                        anchors.rightMargin: -2
                        width: 14; height: 14; radius: 7
                        color: accentColor
                        Label {
                            anchors.centerIn: parent
                            text: toolbar.attachedCount
                            color: "#0a1520"
                            font.pixelSize: 8
                            font.bold: true
                        }
                    }
                }

                onClicked: toolbar.attachClicked()

                ToolTip.visible: hovered
                ToolTip.text: toolbar.attachedCount > 0
                    ? toolbar.attachedCount + " archivo(s) adjunto(s)"
                    : "Adjuntar archivo"
                ToolTip.delay: 400
            }

            // Clear attachments button
            ToolButton {
                visible: toolbar.attachedCount > 0
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20

                background: Rectangle {
                    radius: 4
                    color: parent.hovered ? "#3a2020" : "transparent"
                }
                contentItem: Label {
                    text: "\u2715"
                    color: errorColor
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: toolbar.clearAttachments()
                ToolTip.visible: hovered
                ToolTip.text: "Quitar adjuntos"
                ToolTip.delay: 400
            }

            // Code mode toggle
            ToolButton {
                id: codeBtn
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
                checkable: true
                checked: toolbar.codeMode

                background: Rectangle {
                    radius: 6
                    color: codeBtn.checked ? "#1a3a4a" : (codeBtn.hovered ? "#2a3a4a" : "transparent")
                    border.width: codeBtn.checked ? 1 : 0
                    border.color: accentColor
                }

                contentItem: Label {
                    text: "</>"
                    color: codeBtn.checked ? accentColor : textSecondary
                    font.pixelSize: 11
                    font.family: "Consolas"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onToggled: toolbar.codeModeToggled()

                ToolTip.visible: hovered
                ToolTip.text: "Modo codigo"
                ToolTip.delay: 400
            }

            // Separator
            Rectangle { width: 1; Layout.preferredHeight: 20; color: "#2a3a4a" }

            // Key input button
            ToolButton {
                id: keyBtn
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28

                background: Rectangle {
                    radius: 6
                    color: keyBtn.hovered ? "#2a3a4a" : "transparent"
                }

                contentItem: Label {
                    text: "\ud83d\udd11"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: toolbar.keyInputRequested()

                ToolTip.visible: hovered
                ToolTip.text: "Ingresar clave API"
                ToolTip.delay: 400
            }

            // Separator
            Rectangle { width: 1; Layout.preferredHeight: 20; color: "#2a3a4a" }

            // Active provider indicator
            Rectangle {
                Layout.preferredWidth: providerRow.implicitWidth + 12
                Layout.preferredHeight: 24
                radius: 6
                color: providerMa.containsMouse ? "#2a3a4a" : "#1a2a3a"

                Row {
                    id: providerRow
                    anchors.centerIn: parent
                    spacing: 4

                    Rectangle {
                        width: 6; height: 6; radius: 3
                        anchors.verticalCenter: parent.verticalCenter
                        color: {
                            switch(toolbar.activeProvider) {
                                case "chatgpt": return "#74aa9c"
                                case "claude": return "#d4a574"
                                case "devin": return "#7e9cd8"
                                case "ollama": return "#98c379"
                                default: return accentColor
                            }
                        }
                    }
                    Label {
                        text: toolbar.activeProvider || "auto"
                        color: textSecondary
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                    }
                }

                MouseArea {
                    id: providerMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: toolbar.providerSwitchClicked()
                }

                ToolTip.visible: providerMa.containsMouse
                ToolTip.text: "Cambiar proveedor"
                ToolTip.delay: 400
            }

            // Tool count badge
            Rectangle {
                Layout.preferredWidth: toolLabel.implicitWidth + 12
                Layout.preferredHeight: 20
                radius: 10
                color: "#1a2a3a"
                visible: toolbar.toolCount > 0

                Label {
                    id: toolLabel
                    anchors.centerIn: parent
                    text: toolbar.toolCount + " tools"
                    color: textSecondary
                    font.pixelSize: 9
                    font.family: "Segoe UI"
                }
            }

            // System status indicator
            Rectangle {
                Layout.preferredWidth: statusRow.implicitWidth + 10
                Layout.preferredHeight: 20
                radius: 10
                visible: toolbar.systemStatus !== "idle"
                color: {
                    if (toolbar.systemStatus === "processing") return "#1b3d2a"
                    if (toolbar.systemStatus === "error") return "#3d1b1b"
                    return "#1a2a3a"
                }

                Row {
                    id: statusRow
                    anchors.centerIn: parent
                    spacing: 4

                    Rectangle {
                        width: 6; height: 6; radius: 3
                        anchors.verticalCenter: parent.verticalCenter
                        color: {
                            if (toolbar.systemStatus === "processing") return successColor
                            if (toolbar.systemStatus === "error") return errorColor
                            return textSecondary
                        }
                        SequentialAnimation on opacity {
                            running: toolbar.systemStatus === "processing"
                            loops: Animation.Infinite
                            NumberAnimation { from: 1.0; to: 0.3; duration: 600 }
                            NumberAnimation { from: 0.3; to: 1.0; duration: 600 }
                        }
                    }

                    Label {
                        text: {
                            if (toolbar.systemStatus === "processing") return "procesando"
                            if (toolbar.systemStatus === "error") return "error"
                            return toolbar.systemStatus
                        }
                        color: textSecondary
                        font.pixelSize: 9
                        font.family: "Segoe UI"
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Search button
            ToolButton {
                id: searchBtn
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28

                background: Rectangle {
                    radius: 6
                    color: searchBtn.hovered ? "#2a3a4a" : (searchBar.visible ? "#1a3a4a" : "transparent")
                    border.width: searchBar.visible ? 1 : 0
                    border.color: accentColor
                }

                contentItem: Label {
                    text: "\ud83d\udd0d"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: {
                    searchBar.visible = !searchBar.visible
                    if (searchBar.visible) searchInput.forceActiveFocus()
                    toolbar.searchClicked()
                }

                ToolTip.visible: hovered
                ToolTip.text: "Buscar en historial"
                ToolTip.delay: 400
            }

            Item { width: 4 }
        }

        // === Search bar (expandable) ===
        Rectangle {
            id: searchBar
            visible: false
            width: parent.width
            height: 32
            color: "#0a1520"
            border.width: 1
            border.color: "#2a3a4a"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4

                Label {
                    text: "\ud83d\udd0d"
                    font.pixelSize: 11
                    color: textSecondary
                }

                TextField {
                    id: searchInput
                    Layout.fillWidth: true
                    Layout.preferredHeight: 24
                    placeholderText: "Buscar en historial del chat..."
                    placeholderTextColor: "#4a5560"
                    color: "#f7fbfd"
                    font.pixelSize: 11
                    font.family: "Segoe UI"
                    background: Rectangle { color: "transparent" }
                    onTextChanged: {
                        toolbar.searchQuery = text
                    }
                }

                ToolButton {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    contentItem: Label {
                        text: "\u2715"
                        color: textSecondary
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 4
                        color: parent.hovered ? "#2a3a4a" : "transparent"
                    }
                    onClicked: {
                        searchInput.text = ""
                        searchBar.visible = false
                    }
                }
            }
        }
    }
}
