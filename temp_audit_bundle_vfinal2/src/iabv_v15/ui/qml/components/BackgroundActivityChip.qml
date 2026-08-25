import QtQuick 2.15
import QtQuick.Controls 2.15

/*
  Chip que muestra actividad en segundo plano.
  Propiedades: activityText, progress (0-100), status (idle|running|completed|failed)
  Clickable para expandir/detalle.
*/
Rectangle {
    id: root
    
    property string activityText: ""
    property real progress: 0
    property string status: "idle"
    property bool expanded: false
    property var details: []
    
    signal clicked()
    signal cancelRequested()
    
    implicitWidth: Math.max(180, Math.min(320, activityLabel.implicitWidth + 56))
    implicitHeight: expanded ? Math.max(120, detailsColumn.implicitHeight + 60) : 40
    radius: 20
    color: {
        if (root.status === "failed") return "#4a1c1c"
        if (root.status === "completed") return "#1c3d1c"
        return "#18212a"
    }
    border.color: {
        if (root.status === "failed") return "#cf7e7e"
        if (root.status === "completed") return "#8ccf8b"
        if (root.status === "running") return "#73d7d4"
        return "#42505d"
    }
    border.width: 1
    
    Behavior on implicitHeight {
        NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
    }
    
    // Pulsing animation for running state
    SequentialAnimation on opacity {
        running: root.status === "running"
        loops: Animation.Infinite
        NumberAnimation { from: 1.0; to: 0.7; duration: 1000 }
        NumberAnimation { from: 0.7; to: 1.0; duration: 1000 }
    }
    
    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.expanded = !root.expanded
            root.clicked()
        }
        cursorShape: Qt.PointingHandCursor
    }
    
    Row {
        id: compactRow
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8
        spacing: 8
        visible: !root.expanded
        
        BusyIndicator {
            running: root.status === "running"
            implicitWidth: 24
            implicitHeight: 24
            visible: root.status === "running"
        }
        
        Rectangle {
            visible: root.status === "completed"
            width: 24
            height: 24
            radius: 12
            color: "#1c3d1c"
            
            Text {
                anchors.centerIn: parent
                text: "✓"
                color: "#8ccf8b"
                font.pixelSize: 14
                font.bold: true
            }
        }
        
        Rectangle {
            visible: root.status === "failed"
            width: 24
            height: 24
            radius: 12
            color: "#4a1c1c"
            
            Text {
                anchors.centerIn: parent
                text: "✗"
                color: "#cf7e7e"
                font.pixelSize: 14
                font.bold: true
            }
        }
        
        Text {
            id: activityLabel
            anchors.verticalCenter: parent.verticalCenter
            text: root.activityText || "Sin actividad"
            color: "#f7fbfd"
            font.family: "Segoe UI"
            font.pixelSize: 13
            elide: Text.ElideRight
            width: parent.width - 40
        }
    }
    
    Column {
        id: expandedColumn
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        visible: root.expanded
        
        Row {
            spacing: 12
            width: parent.width
            
            BusyIndicator {
                running: root.status === "running"
                implicitWidth: 28
                implicitHeight: 28
                visible: root.status === "running"
            }
            
            Rectangle {
                visible: root.status === "completed"
                width: 28
                height: 28
                radius: 14
                color: "#1c3d1c"
                
                Text {
                    anchors.centerIn: parent
                    text: "✓"
                    color: "#8ccf8b"
                    font.pixelSize: 16
                    font.bold: true
                }
            }
            
            Rectangle {
                visible: root.status === "failed"
                width: 28
                height: 28
                radius: 14
                color: "#4a1c1c"
                
                Text {
                    anchors.centerIn: parent
                    text: "✗"
                    color: "#cf7e7e"
                    font.pixelSize: 16
                    font.bold: true
                }
            }
            
            Label {
                text: root.activityText || "Sin actividad"
                color: "#f7fbfd"
                font.family: "Segoe UI"
                font.pixelSize: 14
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        
        // Progress bar
        Rectangle {
            width: parent.width
            height: 6
            radius: 3
            color: "#111417"
            
            Rectangle {
                width: parent.width * (Math.max(0, Math.min(100, root.progress)) / 100)
                height: parent.height
                radius: 3
                color: {
                    if (root.status === "failed") return "#cf7e7e"
                    if (root.status === "completed") return "#8ccf8b"
                    return "#73d7d4"
                }
                
                Behavior on width {
                    NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
                }
            }
        }
        
        Label {
            text: Math.round(root.progress) + "%"
            color: "#8a9aaf"
            font.family: "Segoe UI"
            font.pixelSize: 11
        }
        
        // Details list
        Column {
            id: detailsColumn
            width: parent.width
            spacing: 4
            
            Repeater {
                model: root.details
                
                Label {
                    text: "• " + modelData
                    color: "#d1d8df"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
            }
        }
        
        // Cancel button (only when running)
        Button {
            visible: root.status === "running"
            text: "Cancelar"
            width: parent.width
            contentItem: Text {
                text: parent.text
                color: "#cf7e7e"
                font.family: "Segoe UI"
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
            }
            background: Rectangle {
                color: parent.hovered ? "#4a1c1c" : "transparent"
                border.color: "#cf7e7e"
                border.width: 1
                radius: 8
                implicitHeight: 32
            }
            onClicked: root.cancelRequested()
        }
    }
}
