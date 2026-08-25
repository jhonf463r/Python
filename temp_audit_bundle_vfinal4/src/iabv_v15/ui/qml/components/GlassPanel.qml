import QtQuick 2.15

Rectangle {
    id: panel
    property color fillColor: "#1d2630"
    property color strokeColor: "#3c4854"
    radius: 24
    color: fillColor
    border.color: strokeColor
    border.width: 1
}
