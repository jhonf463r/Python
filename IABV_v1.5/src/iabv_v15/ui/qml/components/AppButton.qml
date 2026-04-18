import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: control
    property bool accent: false
    property color fillColor: accent ? "#245e67" : "#28333d"
    property color hoverFillColor: accent ? "#2d6f79" : "#32414c"
    property color pressedFillColor: accent ? "#194750" : "#1c252d"
    property color borderColor: accent ? "#7cd5d2" : "#455361"
    property color textColor: "#f7fbfd"
    property int minButtonWidth: 132
    property int maxButtonWidth: 240

    leftPadding: 16
    rightPadding: 16
    topPadding: 10
    bottomPadding: 10
    implicitWidth: Math.max(minButtonWidth, Math.min(maxButtonWidth, contentItem.implicitWidth + leftPadding + rightPadding))
    implicitHeight: Math.max(48, contentItem.implicitHeight + topPadding + bottomPadding)
    hoverEnabled: true
    font.family: "Segoe UI"
    font.pixelSize: 14
    font.bold: true

    contentItem: Text {
        text: control.text
        color: control.textColor
        font: control.font
        width: control.availableWidth
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        wrapMode: Text.WordWrap
        maximumLineCount: 2
    }

    background: Rectangle {
        radius: 14
        color: control.down ? control.pressedFillColor : (control.hovered ? control.hoverFillColor : control.fillColor)
        border.width: 1
        border.color: control.borderColor
    }
}
