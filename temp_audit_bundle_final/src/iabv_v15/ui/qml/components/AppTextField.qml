import QtQuick 2.15
import QtQuick.Controls 2.15

TextField {
    id: control
    property color fillColor: "#162028"
    property color strokeColor: activeFocus ? "#73d7d4" : "#465462"
    property color fieldTextColor: "#f7fbfd"
    property color hintTextColor: "#b7c0c8"

    implicitHeight: 46
    color: fieldTextColor
    placeholderTextColor: hintTextColor
    selectedTextColor: "#0f1519"
    selectionColor: "#73d7d4"
    font.family: "Segoe UI"
    font.pixelSize: 14
    leftPadding: 14
    rightPadding: 14
    topPadding: 12
    bottomPadding: 12

    background: Rectangle {
        radius: 14
        color: control.fillColor
        border.width: 1
        border.color: control.strokeColor
    }
}
