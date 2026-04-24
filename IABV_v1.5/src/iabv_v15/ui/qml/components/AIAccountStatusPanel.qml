import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * AIAccountStatusPanel — panel glassmorphism que muestra el estado
 * de cuentas de IA (activas, agotadas, renovandose).
 *
 * Se alimenta de controlCenterViewModel.accountStatusCards.
 *
 * Cada card muestra: provider, email (parcial), msgs restantes,
 * barra de cuota, y badge de estado.
 */
GlassPanel {
    id: statusPanel
    fillColor: "#1a2530"
    strokeColor: "#3a4e5e"

    property var accountCards: []
    property color textPrimary: "#f7fbfd"
    property color textSecondary: "#d1d8df"
    property color accentGreen: "#00e676"
    property color accentOrange: "#ffab00"
    property color accentRed: "#ff5252"

    implicitHeight: panelCol.implicitHeight + 28

    Column {
        id: panelCol
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            width: parent.width
            spacing: 8
            Label {
                text: "\u26A1"
                font.pixelSize: 16
            }
            Label {
                text: "Estado de cuentas IA"
                color: textPrimary
                font.pixelSize: 16
                font.family: "Segoe UI"
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                text: accountCards.length + " cuentas"
                color: textSecondary
                font.pixelSize: 11
                font.family: "Segoe UI"
            }
        }

        Repeater {
            model: accountCards
            delegate: Rectangle {
                width: panelCol.width
                radius: 12
                color: "#1d2d3a"
                border.width: 1
                border.color: modelData.status === "active" ? "#2a4a3a" :
                              modelData.status === "exhausted" ? "#4a2a2a" : "#3a3a2a"
                implicitHeight: cardCol.implicitHeight + 16

                Column {
                    id: cardCol
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6

                    RowLayout {
                        width: parent.width
                        spacing: 8

                        // Provider badge
                        Rectangle {
                            width: 28; height: 28
                            radius: 14
                            color: modelData.provider === "chatgpt" ? "#10a37f" :
                                   modelData.provider === "claude" ? "#cc785c" :
                                   modelData.provider === "codex" ? "#6366f1" :
                                   modelData.provider === "ollama" ? "#7c3aed" :
                                   modelData.provider === "devin" ? "#00bcd4" : "#546e7a"
                            Label {
                                anchors.centerIn: parent
                                text: modelData.provider.charAt(0).toUpperCase()
                                color: "white"
                                font.pixelSize: 13
                                font.weight: Font.Bold
                                font.family: "Segoe UI"
                            }
                        }

                        Column {
                            Layout.fillWidth: true
                            spacing: 2
                            Label {
                                text: modelData.provider
                                color: textPrimary
                                font.pixelSize: 13
                                font.family: "Segoe UI"
                                font.weight: Font.DemiBold
                            }
                            Label {
                                text: modelData.email_masked || ""
                                color: textSecondary
                                font.pixelSize: 10
                                font.family: "Segoe UI"
                                visible: text.length > 0
                            }
                        }

                        // Status badge
                        Rectangle {
                            width: statusLabel.width + 14; height: 22
                            radius: 11
                            color: modelData.status === "active" ? "#0d3320" :
                                   modelData.status === "exhausted" ? "#3d0d0d" : "#3d330d"
                            border.width: 1
                            border.color: modelData.status === "active" ? accentGreen :
                                          modelData.status === "exhausted" ? accentRed : accentOrange
                            Label {
                                id: statusLabel
                                anchors.centerIn: parent
                                text: modelData.status === "active" ? "Activa" :
                                      modelData.status === "exhausted" ? "Agotada" :
                                      modelData.status === "renewing" ? "Renovando" : modelData.status
                                color: modelData.status === "active" ? accentGreen :
                                       modelData.status === "exhausted" ? accentRed : accentOrange
                                font.pixelSize: 10
                                font.family: "Segoe UI"
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    // Quota bar
                    Rectangle {
                        width: parent.width
                        height: 6
                        radius: 3
                        color: "#0d1920"
                        visible: modelData.messages_limit > 0

                        Rectangle {
                            width: parent.width * Math.max(0, Math.min(1, modelData.quota_fraction || 0))
                            height: parent.height
                            radius: 3
                            color: (modelData.quota_fraction || 0) > 0.3 ? accentGreen :
                                   (modelData.quota_fraction || 0) > 0.1 ? accentOrange : accentRed
                        }
                    }

                    RowLayout {
                        width: parent.width
                        visible: modelData.messages_limit > 0
                        Label {
                            text: (modelData.messages_remaining || 0) + " / " + (modelData.messages_limit || 0) + " msgs"
                            color: textSecondary
                            font.pixelSize: 10
                            font.family: "Segoe UI"
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: modelData.hours_until_exhaustion
                                  ? ("~" + modelData.hours_until_exhaustion + "h restantes")
                                  : ""
                            color: textSecondary
                            font.pixelSize: 10
                            font.family: "Segoe UI"
                            visible: text.length > 0
                        }
                    }

                    // Confidence indicator
                    RowLayout {
                        width: parent.width
                        visible: (modelData.success_rate || 0) > 0
                        spacing: 6
                        Label {
                            text: "Confianza:"
                            color: textSecondary
                            font.pixelSize: 10
                            font.family: "Segoe UI"
                        }
                        Repeater {
                            model: 5
                            Rectangle {
                                width: 8; height: 8; radius: 4
                                color: index < Math.round((modelData.success_rate || 0) * 5)
                                       ? accentGreen : "#1a2a35"
                            }
                        }
                        Label {
                            text: Math.round((modelData.success_rate || 1) * 100) + "%"
                            color: textSecondary
                            font.pixelSize: 10
                            font.family: "Segoe UI"
                        }
                    }
                }
            }
        }

        // Footer: sin cuentas
        Label {
            visible: accountCards.length === 0
            width: parent.width
            text: "No hay cuentas registradas. Agrega cuentas desde el menu de configuracion."
            color: textSecondary
            font.pixelSize: 11
            font.family: "Segoe UI"
            wrapMode: Label.WordWrap
            horizontalAlignment: Label.AlignHCenter
        }
    }
}
