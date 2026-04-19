import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/*
  Dialog no-modal para solicitar aclaración al usuario.
  Propiedades: question, options (array de strings), context
  Emite: clarificationResponse({id, selectedOption, customText})
*/
Popup {
    id: root
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape
    
    property string requestId: ""
    property string question: ""
    property var options: []
    property string context: ""
    
    signal clarificationResponse(var payload)
    
    width: Math.min(480, parent.width * 0.9)
    x: (parent.width - width) / 2
    y: parent.height - height - 24
    
    background: Rectangle {
        color: "#1b232b"
        border.color: "#73d7d4"
        border.width: 1
        radius: 14
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16
        
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            
            Rectangle {
                width: 32
                height: 32
                radius: 16
                color: "#245e67"
                
                Text {
                    anchors.centerIn: parent
                    text: "?"
                    color: "#f7fbfd"
                    font.family: "Segoe UI"
                    font.pixelSize: 16
                    font.bold: true
                }
            }
            
            Label {
                text: "Aclaración requerida"
                color: "#f7fbfd"
                font.family: "Segoe UI"
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }
            
            Button {
                text: "×"
                flat: true
                implicitWidth: 32
                implicitHeight: 32
                contentItem: Text {
                    text: parent.text
                    color: "#d1d8df"
                    font.pixelSize: 20
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.hovered ? "#28333d" : "transparent"
                    radius: 16
                }
                onClicked: root.close()
            }
        }
        
        Label {
            text: root.question
            color: "#f7fbfd"
            font.family: "Segoe UI"
            font.pixelSize: 14
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        Label {
            visible: root.context.length > 0
            text: "Contexto: " + root.context
            color: "#8a9aaf"
            font.family: "Segoe UI"
            font.pixelSize: 12
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            
            Repeater {
                model: root.options
                
                Button {
                    Layout.fillWidth: true
                    text: modelData
                    contentItem: Text {
                        text: parent.text
                        color: "#f7fbfd"
                        font.family: "Segoe UI"
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    background: Rectangle {
                        color: parent.hovered ? "#245e67" : "#28333d"
                        border.color: parent.hovered ? "#73d7d4" : "#42505d"
                        border.width: 1
                        radius: 10
                        implicitHeight: 44
                    }
                    onClicked: {
                        root.clarificationResponse({
                            id: root.requestId,
                            selectedOption: modelData,
                            customText: ""
                        })
                        root.close()
                    }
                }
            }
        }
        
        TextArea {
            id: customResponse
            visible: root.options.length === 0
            Layout.fillWidth: true
            Layout.minimumHeight: 80
            placeholderText: "Escribe tu respuesta..."
            color: "#f7fbfd"
            placeholderTextColor: "#6b7b8c"
            font.family: "Segoe UI"
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            background: Rectangle {
                color: "#111417"
                border.color: customResponse.activeFocus ? "#73d7d4" : "#42505d"
                border.width: 1
                radius: 8
            }
        }
        
        Button {
            visible: root.options.length === 0
            Layout.fillWidth: true
            enabled: customResponse.text.length > 0
            text: "Enviar respuesta"
            contentItem: Text {
                text: parent.text
                color: enabled ? "#f7fbfd" : "#6b7b8c"
                font.family: "Segoe UI"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: enabled ? (parent.hovered ? "#2d6f79" : "#245e67") : "#1c252d"
                border.color: enabled ? "#7cd5d2" : "#42505d"
                border.width: 1
                radius: 10
                implicitHeight: 44
            }
            onClicked: {
                root.clarificationResponse({
                    id: root.requestId,
                    selectedOption: "",
                    customText: customResponse.text
                })
                root.close()
            }
        }
    }
    
    onOpened: {
        if (root.options.length === 0) {
            customResponse.forceActiveFocus()
        }
    }
}
