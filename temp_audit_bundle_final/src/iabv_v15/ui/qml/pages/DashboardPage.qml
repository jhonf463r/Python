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
    property var summaryCards: dashboardViewModel ? dashboardViewModel.summaryCards : []
    property var providerCards: dashboardViewModel ? dashboardViewModel.providerCards : []
    property string routePolicyText: dashboardViewModel ? dashboardViewModel.routePolicy : "Stack local por roles activo."
    property bool healthBusy: dashboardViewModel ? dashboardViewModel.healthBusy : false
    property string healthStatusText: dashboardViewModel ? dashboardViewModel.healthStatus : "Chequeo pendiente."

    opacity: 0.0
    y: 18
    Behavior on opacity { NumberAnimation { duration: 220 } }
    Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Component.onCompleted: { opacity = 1.0; y = 0 }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            width: pageScroll.availableWidth
            spacing: 16

            Flow {
                width: parent.width
                spacing: 16

                Repeater {
                    model: summaryCards
                    delegate: GlassPanel {
                        width: pageScroll.availableWidth > 1200 ? (pageScroll.availableWidth - 48) / 4 : Math.max(260, pageScroll.availableWidth)
                        fillColor: "#22303a"
                        strokeColor: borderSoft
                        implicitHeight: summaryColumn.implicitHeight + 32

                        Column {
                            id: summaryColumn
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Label {
                                text: modelData.title
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 14
                            }
                            Label {
                                text: modelData.value
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 36
                                font.bold: true
                            }
                            Label {
                                text: modelData.hint
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                                wrapMode: Label.WordWrap
                            }
                        }
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 16

                GlassPanel {
                    width: pageScroll.availableWidth > 1180 ? pageScroll.availableWidth - 396 : pageScroll.availableWidth
                    fillColor: "#1c2630"
                    strokeColor: borderSoft
                    implicitHeight: providerColumn.implicitHeight + 36

                    Column {
                        id: providerColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Pulso del stack local"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 22
                        }

                        Label {
                            text: healthStatusText
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 13
                            wrapMode: Label.WordWrap
                        }

                        Repeater {
                            model: providerCards
                            delegate: Rectangle {
                                width: providerColumn.width
                                radius: 18
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: cardContent.implicitHeight + 24

                                RowLayout {
                                    id: cardContent
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    StatusPill {
                                        label: modelData.status
                                        pulsing: modelData.available
                                        accentColor: modelData.available ? "#2e6770" : "#7b5426"
                                        labelColor: textPrimary
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Label {
                                            text: modelData.provider_name
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 15
                                        }
                                        Label {
                                            text: modelData.detail
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

                GlassPanel {
                    width: pageScroll.availableWidth > 1180 ? 380 : pageScroll.availableWidth
                    fillColor: "#23313b"
                    strokeColor: borderSoft
                    implicitHeight: policyColumn.implicitHeight + 36

                    Column {
                        id: policyColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12
                        Label {
                            text: "Postura operativa"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 22
                        }
                        Label {
                            text: routePolicyText
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 14
                            wrapMode: Label.WordWrap
                        }
                        Flow {
                            width: policyColumn.width
                            spacing: 10
                            AppButton {
                                text: "Actualizar metricas"
                                accent: true
                                onClicked: if (dashboardViewModel) dashboardViewModel.refresh()
                            }
                            AppButton {
                                text: healthBusy ? "Consultando..." : "Consultar stack"
                                enabled: !healthBusy
                                onClicked: if (dashboardViewModel) dashboardViewModel.refreshHealth()
                            }
                        }
                    }
                }
            }
        }
    }
}
