import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/*
  Panel que muestra estado de providers/tools (verde/amarillo/rojo).
  Propiedades: providers (array de {name, status, detail, latency})
  Botones: "Rotar tool" y "Pedir ayuda a Devin"
  Emite: rotateToolRequested(), helpRequested()
*/
Rectangle {
    id: root
    
    property var providers: []
    property string lastUpdated: ""
    property bool loading: false
    
    signal rotateToolRequested()
    signal helpRequested()
    signal refreshRequested()
    signal providerClicked(var provider)
    
    implicitWidth: 320
    implicitHeight: contentColumn.implicitHeight + 40
    radius: 14
    color: "#1b232b"
    border.color: "#42505d"
    border.width: 1
    
    function statusColor(status) {
        if (status === "ready" || status === "available" || status === "green") return "#8ccf8b"
        if (status === "degraded" || status === "warning" || status === "yellow") return "#d9b15f"
        if (status === "unavailable" || status === "error" || status === "red" || status === "failed") return "#cf7e7e"
        if (status === "optional_inactive" || status === "idle") return "#6b7b8c"
        return "#42505d"
    }
    
    function statusText(status) {
        if (status === "ready" || status === "available" || status === "green") return "Listo"
        if (status === "degraded" || status === "warning" || status === "yellow") return "Degradado"
        if (status === "unavailable" || status === "error" || status === "red" || status === "failed") return "No disponible"
        if (status === "optional_inactive") return "Opcional"
        if (status === "idle") return "Inactivo"
        return status
    }
    
    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        
        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            Label {
                text: "Estado de herramientas"
                color: "#f7fbfd"
                font.family: "Segoe UI"
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }
            
            BusyIndicator {
                running: root.loading
                implicitWidth: 20
                implicitHeight: 20
            }
            
            Button {
                text: "↻"
                flat: true
                implicitWidth: 32
                implicitHeight: 32
                contentItem: Text {
                    text: parent.text
                    color: "#d1d8df"
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.hovered ? "#28333d" : "transparent"
                    radius: 16
                }
                onClicked: root.refreshRequested()
            }
        }
        
        Label {
            visible: root.lastUpdated.length > 0
            text: "Actualizado: " + root.lastUpdated
            color: "#6b7b8c"
            font.family: "Segoe UI"
            font.pixelSize: 11
        }
        
        // Provider list
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            
            Repeater {
                model: root.providers
                
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: providerRow.implicitHeight + 16
                    color: "#111417"
                    border.color: {
                        var s = modelData.status || ""
                        if (s === "ready" || s === "available" || s === "green") return "#1c3d1c"
                        if (s === "degraded" || s === "warning" || s === "yellow") return "#3d351c"
                        if (s === "unavailable" || s === "error" || s === "red" || s === "failed") return "#3d1c1c"
                        return "#1c252d"
                    }
                    border.width: 1
                    radius: 10
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.providerClicked(modelData)
                        cursorShape: Qt.PointingHandCursor
                    }
                    
                    RowLayout {
                        id: providerRow
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 10
                        
                        Rectangle {
                            width: 12
                            height: 12
                            radius: 6
                            color: root.statusColor(modelData.status || "")
                        }
                        
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            
                            Label {
                                text: modelData.name || "Unknown"
                                color: "#f7fbfd"
                                font.family: "Segoe UI"
                                font.pixelSize: 14
                                font.bold: true
                            }
                            
                            Label {
                                text: root.statusText(modelData.status || "")
                                color: root.statusColor(modelData.status || "")
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                            }
                            
                            Label {
                                visible: (modelData.detail || "").length > 0
                                text: modelData.detail || ""
                                color: "#8a9aaf"
                                font.family: "Segoe UI"
                                font.pixelSize: 11
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                            }
                            
                            Label {
                                visible: (modelData.latency || 0) > 0
                                text: "Latencia: " + Math.round(modelData.latency) + "ms"
                                color: "#6b7b8c"
                                font.family: "Segoe UI"
                                font.pixelSize: 10
                            }
                        }
                    }
                }
            }
            
            // Empty state
            Label {
                visible: root.providers.length === 0 && !root.loading
                text: "No hay herramientas configuradas"
                color: "#6b7b8c"
                font.family: "Segoe UI"
                font.pixelSize: 13
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
            }
        }
        
        // Summary stats
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            visible: root.providers.length > 0
            
            Label {
                text: {
                    var ready = 0
                    for (var i = 0; i < root.providers.length; i++) {
                        var s = root.providers[i].status || ""
                        if (s === "ready" || s === "available" || s === "green") ready++
                    }
                    return ready + " listas"
                }
                color: "#8ccf8b"
                font.family: "Segoe UI"
                font.pixelSize: 12
            }
            
            Label {
                text: {
                    var degraded = 0
                    for (var i = 0; i < root.providers.length; i++) {
                        var s = root.providers[i].status || ""
                        if (s === "degraded" || s === "warning" || s === "yellow") degraded++
                    }
                    return degraded > 0 ? degraded + " degradadas" : ""
                }
                visible: text.length > 0
                color: "#d9b15f"
                font.family: "Segoe UI"
                font.pixelSize: 12
            }
            
            Label {
                text: {
                    var failed = 0
                    for (var i = 0; i < root.providers.length; i++) {
                        var s = root.providers[i].status || ""
                        if (s === "unavailable" || s === "error" || s === "red" || s === "failed") failed++
                    }
                    return failed > 0 ? failed + " fallidas" : ""
                }
                visible: text.length > 0
                color: "#cf7e7e"
                font.family: "Segoe UI"
                font.pixelSize: 12
            }
        }
        
        // Action buttons
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            
            Button {
                Layout.fillWidth: true
                text: "Rotar tool"
                contentItem: Text {
                    text: parent.text
                    color: "#f7fbfd"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                }
                background: Rectangle {
                    color: parent.hovered ? "#2d6f79" : "#245e67"
                    border.color: "#7cd5d2"
                    border.width: 1
                    radius: 10
                    implicitHeight: 40
                }
                onClicked: root.rotateToolRequested()
            }
            
            Button {
                Layout.fillWidth: true
                text: "Pedir ayuda a Devin"
                contentItem: Text {
                    text: parent.text
                    color: "#f7fbfd"
                    font.family: "Segoe UI"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                }
                background: Rectangle {
                    color: parent.hovered ? "#3d4a5a" : "#28333d"
                    border.color: "#42505d"
                    border.width: 1
                    radius: 10
                    implicitHeight: 40
                }
                onClicked: root.helpRequested()
            }
        }
    }
}
