import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/*
  Dialog modal para aprobar/rechazar instalación de dependencias.
  Propiedades: packageName, manager, reason
  Emite: dependencyApproved({packageName, manager})
         dependencyRejected({packageName, reason})
*/
Dialog {
    id: root
    modal: true
    focus: true
    closePolicy: Dialog.NoAutoClose
    
    property string packageName: ""
    property string manager: ""
    property string reason: ""
    property bool installing: false
    property string installProgress: ""
    
    signal dependencyApproved(var payload)
    signal dependencyRejected(var payload)
    
    title: "Dependencia faltante"
    
    width: Math.min(420, parent.width * 0.9)
    anchors.centerIn: parent
    
    background: Rectangle {
        color: "#1b232b"
        border.color: "#42505d"
        border.width: 1
        radius: 14
    }
    
    header: Rectangle {
        color: "#18212a"
        height: 56
        radius: 14
        
        Label {
            anchors.fill: parent
            anchors.margins: 16
            text: root.title
            color: "#f7fbfd"
            font.family: "Segoe UI"
            font.pixelSize: 18
            font.bold: true
            verticalAlignment: Text.AlignVCenter
        }
    }
    
    contentItem: ColumnLayout {
        spacing: 16
        
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 64
            color: "#111417"
            border.color: "#c98a3d"
            border.width: 1
            radius: 10
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                
                Rectangle {
                    width: 40
                    height: 40
                    radius: 20
                    color: "#c98a3d"
                    
                    Text {
                        anchors.centerIn: parent
                        text: "⚠"
                        color: "#111417"
                        font.pixelSize: 20
                    }
                }
                
                ColumnLayout {
                    spacing: 4
                    
                    Label {
                        text: root.packageName
                        color: "#f7fbfd"
                        font.family: "Segoe UI"
                        font.pixelSize: 15
                        font.bold: true
                    }
                    
                    Label {
                        text: "Gestor: " + root.manager
                        color: "#d1d8df"
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                    }
                }
            }
        }
        
        Label {
            text: "Motivo:"
            color: "#8a9aaf"
            font.family: "Segoe UI"
            font.pixelSize: 12
        }
        
        Label {
            text: root.reason
            color: "#d1d8df"
            font.family: "Segoe UI"
            font.pixelSize: 13
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        Rectangle {
            visible: root.installing
            Layout.fillWidth: true
            implicitHeight: 36
            color: "#111417"
            border.color: "#245e67"
            border.width: 1
            radius: 8
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8
                
                BusyIndicator {
                    running: root.installing
                    implicitWidth: 20
                    implicitHeight: 20
                }
                
                Label {
                    text: root.installProgress || "Instalando..."
                    color: "#d1d8df"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                }
            }
        }
    }
    
    footer: RowLayout {
        spacing: 12
        
        Button {
            text: "Rechazar"
            Layout.fillWidth: true
            enabled: !root.installing
            flat: true
            contentItem: Text {
                text: parent.text
                color: enabled ? "#d1d8df" : "#6b7b8c"
                font.family: "Segoe UI"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: enabled ? (parent.hovered ? "#28333d" : "transparent") : "transparent"
                border.color: enabled ? "#42505d" : "#2a343e"
                border.width: 1
                radius: 10
                implicitHeight: 44
            }
            onClicked: {
                root.dependencyRejected({
                    packageName: root.packageName,
                    reason: "Usuario rechazó la instalación"
                })
                root.close()
            }
        }
        
        Button {
            text: "Aprobar e instalar"
            Layout.fillWidth: true
            enabled: !root.installing
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
                root.dependencyApproved({
                    packageName: root.packageName,
                    manager: root.manager
                })
                root.close()
            }
        }
    }
}
