import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color borderSoft: "#42505d"
    readonly property color accentCyan: "#73d7d4"
    readonly property color accentAmber: "#c98a3d"
    readonly property color accentGreen: "#6fcf97"
    readonly property color accentRed: "#eb5757"
    readonly property string titleFontFamily: "Segoe UI"
    readonly property string bodyFontFamily: "Segoe UI"

    property var orchestratorQueue: centroVivoViewModel ? centroVivoViewModel.orchestratorQueue : []
    property var iaDistribution: centroVivoViewModel ? centroVivoViewModel.iaDistribution : []
    property var heuristicDecisions: centroVivoViewModel ? centroVivoViewModel.heuristicDecisions : []
    property var experimentMetrics: centroVivoViewModel ? centroVivoViewModel.experimentMetrics : []
    property var learningGaps: centroVivoViewModel ? centroVivoViewModel.learningGaps : []
    property var selfExaminationFindings: centroVivoViewModel ? centroVivoViewModel.selfExaminationFindings : []
    property var worldModelSummary: centroVivoViewModel ? centroVivoViewModel.worldModelSummary : ({})

    GlassPanel {
        anchors.fill: parent
        fillColor: "#1c2630"
        strokeColor: borderSoft

        ScrollView {
            id: vivoScroll
            anchors.fill: parent
            anchors.margins: 18
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Column {
                width: vivoScroll.availableWidth
                spacing: 16

                // --- Header ---
                RowLayout {
                    width: parent.width
                    spacing: 14

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: "Centro Vivo"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Label {
                            text: centroVivoViewModel ? centroVivoViewModel.statusText : "Sin estado."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 13
                            wrapMode: Label.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    AppButton {
                        text: "Actualizar"
                        accent: true
                        onClicked: if (centroVivoViewModel) centroVivoViewModel.refresh()
                    }
                }

                // --- World Model Summary (top strip) ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#1c2a33"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: worldModelRow.implicitHeight + 28

                    RowLayout {
                        id: worldModelRow
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 20

                        Column {
                            spacing: 2
                            Label { text: "Ventanas"; color: textSecondary; font.pixelSize: 11; font.family: bodyFontFamily }
                            Label { text: String(worldModelSummary.window_count || 0); color: textPrimary; font.pixelSize: 22; font.bold: true; font.family: titleFontFamily }
                        }
                        Column {
                            spacing: 2
                            Label { text: "Foco"; color: textSecondary; font.pixelSize: 11; font.family: bodyFontFamily }
                            Label {
                                text: {
                                    var f = worldModelSummary.focus_window || ""
                                    if (typeof f === "object") f = f.title || f.process || ""
                                    return f || "—"
                                }
                                color: accentCyan; font.pixelSize: 13; font.family: bodyFontFamily
                                elide: Label.ElideRight
                                Layout.maximumWidth: 200
                            }
                        }
                        Column {
                            spacing: 2
                            Label { text: "Herramientas"; color: textSecondary; font.pixelSize: 11; font.family: bodyFontFamily }
                            Label {
                                text: (worldModelSummary.tools_ready || 0) + "/" + (worldModelSummary.tool_count || 0) + " listas"
                                color: (worldModelSummary.tools_degraded || 0) > 0 ? accentAmber : accentGreen
                                font.pixelSize: 13; font.family: bodyFontFamily
                            }
                        }
                        Column {
                            spacing: 2
                            Label { text: "Red"; color: textSecondary; font.pixelSize: 11; font.family: bodyFontFamily }
                            Label {
                                text: worldModelSummary.network_connected ? "Conectada" : "Sin red"
                                color: worldModelSummary.network_connected ? accentGreen : accentRed
                                font.pixelSize: 13; font.family: bodyFontFamily
                            }
                        }
                    }
                }

                // --- Orchestrator Queue ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: queueCol.implicitHeight + 28

                    Column {
                        id: queueCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Cola del Orquestador"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: orchestratorQueue.length === 0
                            text: "Sin sesiones en cola."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: orchestratorQueue
                            delegate: Rectangle {
                                width: queueCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: queueItemCol.implicitHeight + 16

                                Column {
                                    id: queueItemCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    RowLayout {
                                        width: parent.width
                                        Label {
                                            text: modelData.user_goal || "(sin objetivo)"
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 13
                                            elide: Label.ElideRight
                                            Layout.fillWidth: true
                                        }
                                        StatusPill {
                                            label: modelData.status || "—"
                                            pillColor: {
                                                var s = modelData.status || ""
                                                if (s === "executing") return accentCyan
                                                if (s === "completed") return accentGreen
                                                if (s === "failed" || s === "aborted") return accentRed
                                                return accentAmber
                                            }
                                        }
                                    }
                                    Label {
                                        visible: (modelData.chosen_pack || "") !== ""
                                        text: "Pack: " + (modelData.chosen_pack || "")
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }

                // --- IA Distribution ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: iaCol.implicitHeight + 28

                    Column {
                        id: iaCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Reparto entre IAs"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: iaDistribution.length === 0
                            text: "Sin herramientas registradas."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Flow {
                            width: parent.width
                            spacing: 8

                            Repeater {
                                model: iaDistribution
                                delegate: Rectangle {
                                    width: Math.max(160, (iaCol.width - 24) / 3)
                                    height: 70
                                    radius: 10
                                    color: "#2a3640"
                                    border.width: 1
                                    border.color: borderSoft

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 4

                                        Label {
                                            text: modelData.tool_id || "—"
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 13
                                            font.bold: true
                                            elide: Label.ElideRight
                                            width: parent.width
                                        }
                                        Label {
                                            text: (modelData.status || "—") + (modelData.category ? (" · " + modelData.category) : "")
                                            color: {
                                                var s = modelData.status || ""
                                                if (s === "ready") return accentGreen
                                                if (s === "degraded") return accentAmber
                                                return textSecondary
                                            }
                                            font.family: bodyFontFamily
                                            font.pixelSize: 11
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // --- Heuristic Decisions ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: heuristicCol.implicitHeight + 28

                    Column {
                        id: heuristicCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Decisiones de Ruta (Heuristica)"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: heuristicDecisions.length === 0
                            text: "Sin recomendaciones registradas."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: heuristicDecisions
                            delegate: Rectangle {
                                width: heuristicCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: heuristicItemCol.implicitHeight + 16

                                Column {
                                    id: heuristicItemCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    RowLayout {
                                        width: parent.width
                                        Label {
                                            text: (modelData.domain || "") + " / " + (modelData.subject_key || "")
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 13
                                            Layout.fillWidth: true
                                        }
                                        Label {
                                            text: "Ganador: " + (modelData.winner_label || "—")
                                            color: accentCyan
                                            font.family: bodyFontFamily
                                            font.pixelSize: 12
                                        }
                                    }
                                    Label {
                                        text: "Ventaja: " + (modelData.advantage_pct || 0).toFixed(1) + "% | Confianza: " + (modelData.confidence || 0).toFixed(2)
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }

                // --- Experiment Metrics ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: metricsCol.implicitHeight + 28

                    Column {
                        id: metricsCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Metricas del Laboratorio"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: experimentMetrics.length === 0
                            text: "Sin experimentos registrados."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: experimentMetrics
                            delegate: Rectangle {
                                width: metricsCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: metricsItemRow.implicitHeight + 16

                                RowLayout {
                                    id: metricsItemRow
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 12

                                    Label {
                                        text: modelData.candidate_label || modelData.assistant_kind || "—"
                                        color: textPrimary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 13
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: "Score: " + (modelData.score || 0).toFixed(2)
                                        color: accentCyan
                                        font.family: bodyFontFamily
                                        font.pixelSize: 12
                                    }
                                    Label {
                                        text: (modelData.domain || "")
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }

                // --- Learning Gaps (Research Backlog) ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: gapsCol.implicitHeight + 28

                    Column {
                        id: gapsCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Areas de Investigacion Pendientes"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: learningGaps.length === 0
                            text: "Sin areas de investigacion pendientes."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: learningGaps
                            delegate: Rectangle {
                                width: gapsCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: gapItemCol.implicitHeight + 16

                                Column {
                                    id: gapItemCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    RowLayout {
                                        width: parent.width
                                        StatusPill {
                                            label: modelData.kind || "—"
                                            pillColor: accentAmber
                                        }
                                        Label {
                                            text: modelData.label || ""
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 13
                                            Layout.fillWidth: true
                                        }
                                    }
                                    Label {
                                        text: modelData.research_hint || ""
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                }
                            }
                        }
                    }
                }

                // --- Self-Examination Findings ---
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: findingsCol.implicitHeight + 28

                    Column {
                        id: findingsCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Hallazgos de Autoexaminacion"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }

                        Label {
                            visible: selfExaminationFindings.length === 0
                            text: "Sin hallazgos de autoexaminacion."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: selfExaminationFindings
                            delegate: Rectangle {
                                width: findingsCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: findingItemCol.implicitHeight + 16

                                Column {
                                    id: findingItemCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    RowLayout {
                                        width: parent.width
                                        Label {
                                            text: modelData.title || "—"
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 13
                                            Layout.fillWidth: true
                                        }
                                        StatusPill {
                                            label: modelData.severity || "—"
                                            pillColor: {
                                                var s = modelData.severity || ""
                                                if (s === "high" || s === "critical") return accentRed
                                                if (s === "medium") return accentAmber
                                                return accentGreen
                                            }
                                        }
                                    }
                                    Label {
                                        text: modelData.recommendation || ""
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        visible: (modelData.category || "") !== ""
                                        text: "Categoria: " + (modelData.category || "")
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 10
                                    }
                                }
                            }
                        }
                    }
                }

                // --- Last refresh timestamp ---
                Label {
                    text: centroVivoViewModel ? ("Ultima actualizacion: " + centroVivoViewModel.lastRefreshUtc) : ""
                    color: textSecondary
                    font.family: bodyFontFamily
                    font.pixelSize: 10
                    horizontalAlignment: Label.AlignRight
                    width: parent.width
                }
            }
        }
    }
}
