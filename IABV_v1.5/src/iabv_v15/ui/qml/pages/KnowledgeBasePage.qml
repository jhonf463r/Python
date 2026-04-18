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
    property var itemsModel: knowledgeBaseViewModel ? knowledgeBaseViewModel.items : []

    opacity: 0.0
    y: 18
    Behavior on opacity { NumberAnimation { duration: 220 } }
    Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Component.onCompleted: { opacity = 1.0; y = 0 }

    GlassPanel {
        anchors.fill: parent
        fillColor: "#1c2630"
        strokeColor: borderSoft

        ScrollView {
            id: knowledgeScroll
            anchors.fill: parent
            anchors.margins: 18
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Column {
                width: knowledgeScroll.availableWidth
                spacing: 14

                RowLayout {
                    width: parent.width
                    spacing: 12
                    Label {
                        text: "Base de conocimiento"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 22
                        Layout.fillWidth: true
                    }
                    AppTextField {
                        Layout.preferredWidth: 320
                        placeholderText: "Buscar por titulo, resumen o etiquetas"
                        onTextChanged: if (knowledgeBaseViewModel) knowledgeBaseViewModel.setSearchTerm(text)
                    }
                }

                Label {
                    visible: itemsModel.length === 0
                    text: "Todavia no hay items confirmados. Cuando memorices episodios o payloads apareceran aqui."
                    color: textSecondary
                    font.family: bodyFontFamily
                    font.pixelSize: 13
                    wrapMode: Label.WordWrap
                }

                Repeater {
                    model: itemsModel
                    delegate: Rectangle {
                        width: knowledgeScroll.availableWidth
                        radius: 18
                        color: "#2a3640"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: cardContent.implicitHeight + 24

                        Column {
                            id: cardContent
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 5
                            Label {
                                text: modelData.title
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                                wrapMode: Label.WordWrap
                            }
                            Label {
                                text: modelData.summary
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                            }
                            Label {
                                text: "Confianza: " + Number(modelData.confidence).toFixed(2) + "  |  Etiquetas: " + modelData.tags.join(", ")
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
