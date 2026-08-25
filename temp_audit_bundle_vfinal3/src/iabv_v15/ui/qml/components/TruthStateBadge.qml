import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: badge
    property string truthState: ""

    visible: truthState !== ""
    radius: 8
    implicitWidth: badgeLabel.implicitWidth + 14
    implicitHeight: 20

    color: {
        if (truthState === "observed") return "#1b3d2a"
        if (truthState === "inferred") return "#1a2a3a"
        if (truthState === "unresolved") return "#3d3520"
        return "transparent"
    }
    border.width: 1
    border.color: {
        if (truthState === "observed") return "#2e6e47"
        if (truthState === "inferred") return "#2e4a6e"
        if (truthState === "unresolved") return "#6e5a2e"
        return "transparent"
    }

    Label {
        id: badgeLabel
        anchors.centerIn: parent
        text: {
            if (badge.truthState === "observed") return "OBSERVADO"
            if (badge.truthState === "inferred") return "INFERIDO"
            if (badge.truthState === "unresolved") return "SIN CONFIRMAR"
            return ""
        }
        color: {
            if (badge.truthState === "observed") return "#81c784"
            if (badge.truthState === "inferred") return "#4fc3f7"
            if (badge.truthState === "unresolved") return "#ffb74d"
            return "#d1d8df"
        }
        font.family: "Segoe UI"
        font.pixelSize: 9
        font.bold: true
    }
}
