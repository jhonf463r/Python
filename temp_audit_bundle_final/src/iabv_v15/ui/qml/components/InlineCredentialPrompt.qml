import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/**
 * InlineCredentialPrompt — prompt inline para credenciales dentro
 * del chat. Aparece cuando el sistema necesita una credencial
 * nueva para un provider.
 *
 * Features:
 * - Input con mascara (echoMode: Password)
 * - Toggle para mostrar/ocultar
 * - Checkbox "Recordar para esta cuenta"
 * - Provider badge
 * - Se comunica con controlCenterViewModel.submitCredential()
 */
GlassPanel {
    id: credPrompt
    fillColor: "#1a2838"
    strokeColor: "#4a5e6e"

    property string provider: ""
    property string promptText: ""
    property string credentialRefHint: ""
    property bool visible: false
    property color textPrimary: "#f7fbfd"
    property color textSecondary: "#d1d8df"
    property color accentBlue: "#42a5f5"

    signal credentialSubmitted(string provider, string value, bool remember)
    signal dismissed()

    implicitHeight: promptCol.implicitHeight + 28

    Column {
        id: promptCol
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 28; height: 28
                radius: 14
                color: provider === "chatgpt" ? "#10a37f" :
                       provider === "claude" ? "#cc785c" :
                       provider === "codex" ? "#6366f1" :
                       provider === "devin" ? "#00bcd4" : "#546e7a"
                Label {
                    anchors.centerIn: parent
                    text: provider.length > 0 ? provider.charAt(0).toUpperCase() : "?"
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
                    text: "Credencial requerida: " + provider
                    color: textPrimary
                    font.pixelSize: 14
                    font.family: "Segoe UI"
                    font.weight: Font.DemiBold
                }
                Label {
                    text: promptText || "Ingresa la credencial para continuar."
                    color: textSecondary
                    font.pixelSize: 11
                    font.family: "Segoe UI"
                    wrapMode: Label.WordWrap
                }
            }

            // Close button
            Rectangle {
                width: 24; height: 24; radius: 12
                color: closeMa.containsMouse ? "#3a4a5a" : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "\u2715"
                    color: textSecondary
                    font.pixelSize: 12
                }
                MouseArea {
                    id: closeMa
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: dismissed()
                }
            }
        }

        // Credential input
        RowLayout {
            width: parent.width
            spacing: 8

            TextField {
                id: credInput
                Layout.fillWidth: true
                placeholderText: credentialRefHint || "$env:PROVIDER_KEY"
                echoMode: showToggle.checked ? TextInput.Normal : TextInput.Password
                font.family: "Consolas"
                font.pixelSize: 12
                color: textPrimary
                background: Rectangle {
                    radius: 10
                    color: "#0d1920"
                    border.width: 1
                    border.color: credInput.focus ? accentBlue : "#3a4a5a"
                }
                leftPadding: 12
                rightPadding: 12
                topPadding: 8
                bottomPadding: 8
            }

            CheckBox {
                id: showToggle
                text: "Mostrar"
                font.pixelSize: 10
                font.family: "Segoe UI"
                contentItem: Label {
                    text: parent.text
                    color: textSecondary
                    font: parent.font
                    leftPadding: parent.indicator.width + 4
                    verticalAlignment: Label.AlignVCenter
                }
            }
        }

        RowLayout {
            width: parent.width
            spacing: 8

            CheckBox {
                id: rememberCheck
                text: "Recordar para esta cuenta"
                checked: true
                font.pixelSize: 11
                font.family: "Segoe UI"
                contentItem: Label {
                    text: parent.text
                    color: textSecondary
                    font: parent.font
                    leftPadding: parent.indicator.width + 4
                    verticalAlignment: Label.AlignVCenter
                }
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                width: submitLabel.width + 24; height: 32
                radius: 16
                color: credInput.text.length > 0 ? accentBlue : "#2a3a4a"
                opacity: credInput.text.length > 0 ? 1.0 : 0.5

                Label {
                    id: submitLabel
                    anchors.centerIn: parent
                    text: "Guardar credencial"
                    color: "white"
                    font.pixelSize: 12
                    font.family: "Segoe UI"
                    font.weight: Font.DemiBold
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: credInput.text.length > 0
                    onClicked: {
                        credentialSubmitted(provider, credInput.text, rememberCheck.checked)
                        credInput.text = ""
                    }
                }
            }
        }
    }
}
