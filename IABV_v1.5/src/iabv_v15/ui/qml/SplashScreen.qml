import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: splashWindow
    flags: Qt.SplashScreen | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
    modality: Qt.ApplicationModal
    visible: true
    width: 560
    height: logExpanded ? 620 : 420
    color: "transparent"
    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2

    property bool logExpanded: false
    property bool copyFeedback: false

    readonly property color bgDark: "#0d1117"
    readonly property color bgCard: "#161b22"
    readonly property color accentCyan: "#73d7d4"
    readonly property color accentAmber: "#c98a3d"
    readonly property color textPrimary: "#f0f6fc"
    readonly property color textSecondary: "#8b949e"
    readonly property color borderSoft: "#30363d"
    readonly property color errorRed: "#f85149"
    readonly property color successGreen: "#3fb950"

    Behavior on height {
        NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
    }

    // Close splash when bootstrap signals ready (after short delay)
    Connections {
        target: splashController
        function onReadyChanged() {
            if (splashController.ready) {
                readyDelay.start()
            }
        }
    }

    Timer {
        id: readyDelay
        interval: splashController && splashController.hasError ? 4000 : 1500
        onTriggered: fadeOut.start()
    }

    NumberAnimation {
        id: fadeOut
        target: splashWindow
        property: "opacity"
        from: 1.0; to: 0.0
        duration: 600
        easing.type: Easing.InOutQuad
        onFinished: {
            // Avisamos a Python ANTES de cerrar para poder marcar el
            // hito ``splash_window_closing`` en el startup_timeline.
            // Si este hito aparece pero el splash sigue visible en
            // pantalla, la causa es Z-order / Window Manager y no del
            // codigo Python.
            if (typeof splashController !== "undefined" && splashController) {
                splashController.signal_closing()
            }
            splashWindow.close()
        }
    }

    // Main card
    Rectangle {
        anchors.fill: parent
        radius: 16
        color: bgDark
        border.color: borderSoft
        border.width: 1
        clip: true

        // Subtle glow behind logo
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 36
            width: 110; height: 110
            radius: 55
            color: "transparent"
            border.color: accentCyan
            border.width: 1
            opacity: 0.15
            NumberAnimation on opacity {
                from: 0.08; to: 0.25
                duration: 2000
                loops: Animation.Infinite
                easing.type: Easing.InOutSine
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 10

            // Logo area
            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 72
                Layout.preferredHeight: 72

                Image {
                    id: logoImage
                    anchors.centerIn: parent
                    width: 64; height: 64
                    source: typeof splashController !== "undefined" && splashController.iconPath
                            ? "file:///" + splashController.iconPath : ""
                    fillMode: Image.PreserveAspectFit
                    visible: status === Image.Ready
                    smooth: true
                }

                Text {
                    anchors.centerIn: parent
                    text: "B"
                    font.pixelSize: 42
                    font.bold: true
                    font.family: "Segoe UI"
                    color: accentCyan
                    visible: !logoImage.visible
                }

                SequentialAnimation on scale {
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 1.03; duration: 1200; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 1.03; to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
                }
            }

            // Title
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "BURVE"
                font.pixelSize: 26
                font.bold: true
                font.family: "Segoe UI"
                font.letterSpacing: 6
                color: textPrimary
            }

            // Subtitle
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "IABV v1.5 \u2014 Asistente IA Aut\u00f3nomo"
                font.pixelSize: 12
                font.family: "Segoe UI"
                color: textSecondary
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Gobierno Operativo \u00b7 Metacognici\u00f3n \u00b7 Aprendizaje Adaptativo"
                font.pixelSize: 10
                font.family: "Segoe UI"
                color: Qt.rgba(textSecondary.r, textSecondary.g, textSecondary.b, 0.5)
            }

            Item { Layout.fillHeight: true; Layout.minimumHeight: 8; Layout.maximumHeight: 16 }

            // Progress bar
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 4
                radius: 2
                color: borderSoft

                Rectangle {
                    width: parent.width * (splashController ? splashController.progress : 0)
                    height: parent.height
                    radius: 2
                    color: splashController && splashController.hasError
                           ? errorRed
                           : (splashController && splashController.ready ? successGreen : accentCyan)

                    Behavior on width {
                        NumberAnimation { duration: 400; easing.type: Easing.OutCubic }
                    }
                    Behavior on color {
                        ColorAnimation { duration: 300 }
                    }
                }
            }

            // Status message
            Text {
                Layout.fillWidth: true
                Layout.preferredHeight: 18
                text: splashController ? splashController.status : "Iniciando..."
                font.pixelSize: 12
                font.family: "Segoe UI"
                color: splashController && splashController.hasError
                       ? errorRed
                       : (splashController && splashController.ready ? successGreen : accentCyan)
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                Behavior on color { ColorAnimation { duration: 300 } }
            }

            // Error detail panel (only visible on error)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: errorContent.implicitHeight + 16
                radius: 8
                color: Qt.rgba(errorRed.r, errorRed.g, errorRed.b, 0.06)
                border.color: Qt.rgba(errorRed.r, errorRed.g, errorRed.b, 0.25)
                border.width: 1
                visible: splashController ? splashController.hasError : false

                ColumnLayout {
                    id: errorContent
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    Text {
                        Layout.fillWidth: true
                        text: splashController ? splashController.errorDetail : ""
                        font.pixelSize: 11
                        font.family: "Consolas"
                        color: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.8)
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "El programa intentar\u00e1 continuar. Usa el log para diagn\u00f3stico."
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                        color: textSecondary
                    }
                }
            }

            // Diagnostic toggle + copy buttons row
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                spacing: 8

                // Toggle diagnostic log
                Rectangle {
                    Layout.preferredWidth: logToggleText.implicitWidth + 24
                    Layout.preferredHeight: 26
                    radius: 6
                    color: logToggleArea.containsMouse ? Qt.rgba(accentCyan.r, accentCyan.g, accentCyan.b, 0.12) : "transparent"
                    border.color: Qt.rgba(borderSoft.r, borderSoft.g, borderSoft.b, 0.6)
                    border.width: 1

                    Text {
                        id: logToggleText
                        anchors.centerIn: parent
                        text: logExpanded ? "\u25B2 Ocultar log" : "\u25BC Ver log de arranque"
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                        color: textSecondary
                    }

                    MouseArea {
                        id: logToggleArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: logExpanded = !logExpanded
                    }
                }

                Item { Layout.fillWidth: true }

                // Copy diagnostic button
                Rectangle {
                    Layout.preferredWidth: copyText.implicitWidth + 24
                    Layout.preferredHeight: 26
                    radius: 6
                    color: copyArea.containsMouse ? Qt.rgba(accentAmber.r, accentAmber.g, accentAmber.b, 0.15) : "transparent"
                    border.color: copyFeedback ? successGreen : Qt.rgba(accentAmber.r, accentAmber.g, accentAmber.b, 0.5)
                    border.width: 1

                    Text {
                        id: copyText
                        anchors.centerIn: parent
                        text: copyFeedback ? "\u2713 Copiado" : "\u2398 Copiar reporte"
                        font.pixelSize: 10
                        font.family: "Segoe UI"
                        color: copyFeedback ? successGreen : accentAmber
                    }

                    MouseArea {
                        id: copyArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (splashController) {
                                var logText = splashController.copyDiagnostic()
                                // Copy to clipboard via a hidden TextEdit
                                clipHelper.text = logText
                                clipHelper.selectAll()
                                clipHelper.copy()
                                copyFeedback = true
                                copyResetTimer.start()
                            }
                        }
                    }

                    Timer {
                        id: copyResetTimer
                        interval: 2000
                        onTriggered: copyFeedback = false
                    }
                }
            }

            // Diagnostic log panel (expandable)
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: logExpanded ? 180 : 0
                Layout.maximumHeight: logExpanded ? 400 : 0
                radius: 8
                color: bgCard
                border.color: borderSoft
                border.width: 1
                visible: logExpanded
                clip: true

                Flickable {
                    id: logFlick
                    anchors.fill: parent
                    anchors.margins: 8
                    contentHeight: logTextItem.implicitHeight
                    flickableDirection: Flickable.VerticalFlick
                    clip: true

                    Text {
                        id: logTextItem
                        width: logFlick.width
                        text: splashController ? splashController.diagnosticLog : ""
                        font.pixelSize: 10
                        font.family: "Consolas"
                        color: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.75)
                        wrapMode: Text.WordWrap
                        lineHeight: 1.4
                    }

                    // Auto-scroll to bottom when log updates
                    Connections {
                        target: splashController
                        function onLogChanged() {
                            logFlick.contentY = Math.max(0, logFlick.contentHeight - logFlick.height)
                        }
                    }
                }

                // Scrollbar indicator
                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 2
                    y: parent.height * (logFlick.contentY / Math.max(logFlick.contentHeight, 1))
                    width: 3
                    height: Math.max(20, parent.height * (parent.height / Math.max(logFlick.contentHeight, 1)))
                    radius: 1.5
                    color: Qt.rgba(accentCyan.r, accentCyan.g, accentCyan.b, 0.3)
                    visible: logFlick.contentHeight > logFlick.height
                }
            }

            // Footer
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "local-first \u00b7 observable \u00b7 gobernado"
                font.pixelSize: 10
                font.family: "Segoe UI"
                color: Qt.rgba(textSecondary.r, textSecondary.g, textSecondary.b, 0.35)
            }
        }
    }

    // Hidden helper for clipboard copy
    TextEdit {
        id: clipHelper
        visible: false
    }
}
