import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: pill
    property string label: ""
    property color accentColor: "#2f6d75"
    property color labelColor: "#f7fbfd"
    property bool pulsing: false
    property int minPillWidth: 132
    property int maxPillWidth: 280

    radius: 18
    implicitWidth: Math.max(minPillWidth, Math.min(maxPillWidth, pillLabel.implicitWidth + 26))
    implicitHeight: Math.max(42, pillLabel.implicitHeight + 16)
    color: accentColor
    opacity: 0.96

    SequentialAnimation on opacity {
        running: pill.pulsing
        loops: Animation.Infinite
        NumberAnimation { from: 0.96; to: 0.78; duration: 1100 }
        NumberAnimation { from: 0.78; to: 0.96; duration: 1100 }
    }

    Text {
        id: pillLabel
        anchors.fill: parent
        anchors.margins: 8
        text: pill.label
        color: pill.labelColor
        font.family: "Segoe UI"
        font.pixelSize: 14
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
        maximumLineCount: 2
        elide: Text.ElideRight
    }
}
