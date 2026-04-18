import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color borderSoft: "#42505d"
    readonly property string titleFontFamily: "Segoe UI"
    readonly property string bodyFontFamily: "Segoe UI"
    property var providersModel: providerSettingsViewModel ? providerSettingsViewModel.providers : []
    property string policyTextValue: providerSettingsViewModel ? providerSettingsViewModel.policyText : "Operacion local por roles."
    property string statusLineValue: providerSettingsViewModel ? providerSettingsViewModel.statusLine : "Consulta pendiente."
    property bool busyState: providerSettingsViewModel ? providerSettingsViewModel.healthBusy : false

    function kindLabel(value) {
        if (value === "local") return "local"
        if (value === "cloud") return "nube"
        return value
    }

    opacity: 0.0
    y: 18
    Behavior on opacity { NumberAnimation { duration: 220 } }
    Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Component.onCompleted: { opacity = 1.0; y = 0 }

    ScrollView {
        id: providerScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            width: providerScroll.availableWidth
            spacing: 16

            GlassPanel {
                width: parent.width
                fillColor: "#23313b"
                strokeColor: borderSoft
                implicitHeight: topColumn.implicitHeight + 34

                Column {
                    id: topColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 8
                    Label {
                        text: "Stack local oficial"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 22
                    }
                    Label {
                        text: policyTextValue
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                        wrapMode: Label.WordWrap
                    }
                    Label {
                        text: statusLineValue
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 12
                AppButton {
                    text: "Restablecer tarjetas"
                    onClicked: if (providerSettingsViewModel) providerSettingsViewModel.refresh()
                }
                AppButton {
                    text: busyState ? "Consultando..." : "Actualizar estado"
                    accent: true
                    enabled: !busyState
                    onClicked: if (providerSettingsViewModel) providerSettingsViewModel.refreshHealth()
                }
            }

            Flow {
                width: parent.width
                spacing: 12

                Repeater {
                    model: providersModel
                    delegate: GlassPanel {
                        width: providerScroll.availableWidth > 1180 ? (providerScroll.availableWidth - 12) / 2 : providerScroll.availableWidth
                        fillColor: "#1c2630"
                        strokeColor: borderSoft
                        implicitHeight: providerCardColumn.implicitHeight + 34

                        Column {
                            id: providerCardColumn
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 8
                            Label {
                                text: modelData.name
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 18
                                wrapMode: Label.WordWrap
                            }
                            Label {
                                text: kindLabel(modelData.kind) + "  |  modelo: " + modelData.model
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                            }
                            Label {
                                text: modelData.base_url
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                            }
                            StatusPill {
                                label: modelData.health ? modelData.health.status : "desconocido"
                                accentColor: modelData.health && modelData.health.available ? "#2e6770" : "#7b5426"
                                labelColor: textPrimary
                                pulsing: modelData.health && modelData.health.available
                            }
                            Label {
                                text: modelData.health ? modelData.health.detail : "Sin datos de estado."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
