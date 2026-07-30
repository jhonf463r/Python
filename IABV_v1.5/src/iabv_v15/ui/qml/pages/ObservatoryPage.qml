import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color accentCyan: "#73d7d4"
    readonly property color accentAmber: "#c98a3d"
    readonly property color accentRed: "#e57373"
    readonly property color borderSoft: "#42505d"
    readonly property string titleFontFamily: "Segoe UI"
    readonly property string bodyFontFamily: "Segoe UI"

    property var surfaceContract: observatoryViewModel ? observatoryViewModel.surfaceContract : ({})
    property bool loading: observatoryViewModel ? observatoryViewModel.loading : false
    property string error: observatoryViewModel ? observatoryViewModel.error : ""

    opacity: 0.0
    y: 18
    Behavior on opacity { NumberAnimation { duration: 220 } }
    Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Component.onCompleted: {
        opacity = 1.0
        y = 0
        if (observatoryViewModel) observatoryViewModel.refresh()
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            width: pageScroll.availableWidth
            spacing: 16

            // Header with refresh button
            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: headerColumn.implicitHeight + 28

                Column {
                    id: headerColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    RowLayout {
                        width: parent.width
                        spacing: 12

                        Label {
                            text: "Observatorio del Organismo"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 28
                            font.bold: true
                            Layout.fillWidth: true
                        }

                        AppButton {
                            text: loading ? "Cargando..." : "Actualizar"
                            enabled: !loading
                            accent: true
                            onClicked: if (observatoryViewModel) observatoryViewModel.refresh()
                        }
                    }

                    if (error !== "") {
                        Rectangle {
                            width: parent.width
                            height: errorText.implicitHeight + 16
                            radius: 12
                            color: "#3d2a2a"
                            border.width: 1
                            border.color: accentRed

                            Label {
                                id: errorText
                                anchors.centerIn: parent
                                anchors.margins: 8
                                text: "Error: " + error
                                color: accentRed
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                                wrapMode: Label.WordWrap
                                width: parent.width - 16
                            }
                        }
                    }

                    Label {
                        text: "Última actualización: " + (surfaceContract.timestamp || "Pendiente")
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                    }
                }
            }

            // Human Vision Section
            GlassPanel {
                width: parent.width
                fillColor: "#22303a"
                strokeColor: borderSoft
                implicitHeight: humanVisionColumn.implicitHeight + 32

                Column {
                    id: humanVisionColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Visión Humana"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Label {
                        text: "Dirección del proyecto:"
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                    }
                    Label {
                        text: surfaceContract.human_vision ? surfaceContract.human_vision.current_project_direction || "UNRESOLVED" : "UNRESOLVED"
                        color: textPrimary
                        font.family: bodyFontFamily
                        font.pixelSize: 15
                        wrapMode: Label.WordWrap
                        width: parent.width
                    }

                    Label {
                        text: "Fase actual: " + (surfaceContract.human_vision ? surfaceContract.human_vision.current_phase || "UNRESOLVED" : "UNRESOLVED")
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                    }

                    Label {
                        text: "Siguiente paso recomendado:"
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                    }
                    Label {
                        text: surfaceContract.human_vision ? surfaceContract.human_vision.recommended_next_step || "UNRESOLVED" : "UNRESOLVED"
                        color: textPrimary
                        font.family: bodyFontFamily
                        font.pixelSize: 15
                        wrapMode: Label.WordWrap
                        width: parent.width
                    }

                    Label {
                        text: "Ruta AI recomendada: " + (surfaceContract.human_vision ? surfaceContract.human_vision.recommended_ai_route || "UNRESOLVED" : "UNRESOLVED")
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                    }

                    if (surfaceContract.human_vision && surfaceContract.human_vision.source) {
                        Label {
                            text: "Fuente: " + surfaceContract.human_vision.source
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                        }
                    }

                    // Source Freshness
                    if (surfaceContract.human_vision && surfaceContract.human_vision.source_freshness) {
                        Label {
                            text: "Frescura de fuentes:"
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Repeater {
                            model: Object.keys(surfaceContract.human_vision.source_freshness || {})
                            delegate: Rectangle {
                                width: parent.width
                                height: freshnessColumn.implicitHeight + 12
                                radius: 6
                                color: "#1c2630"
                                border.width: 1
                                border.color: {
                                    var freshness = surfaceContract.human_vision.source_freshness[modelData];
                                    return freshness && freshness.is_stale ? accentAmber : borderSoft;
                                }

                                Column {
                                    id: freshnessColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    Row {
                                        spacing: 8
                                        width: parent.width

                                        Label {
                                            text: modelData
                                            color: textPrimary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 12
                                            font.bold: true
                                        }

                                        Label {
                                            text: {
                                                var freshness = surfaceContract.human_vision.source_freshness[modelData];
                                                if (!freshness) return "UNRESOLVED";
                                                if (freshness.is_stale) return "STALE";
                                                if (freshness.is_fresh) return "FRESH";
                                                return "UNKNOWN";
                                            }
                                            color: {
                                                var freshness = surfaceContract.human_vision.source_freshness[modelData];
                                                if (!freshness) return textSecondary;
                                                if (freshness.is_stale) return accentAmber;
                                                if (freshness.is_fresh) return accentCyan;
                                                return textSecondary;
                                            }
                                            font.family: bodyFontFamily
                                            font.pixelSize: 11
                                            font.bold: true
                                        }
                                    }

                                    Label {
                                        text: {
                                            var freshness = surfaceContract.human_vision.source_freshness[modelData];
                                            if (!freshness || freshness.age_seconds === undefined) return "Edad: UNRESOLVED";
                                            var age = freshness.age_seconds;
                                            if (age < 60) return "Edad: " + Math.round(age) + "s";
                                            if (age < 3600) return "Edad: " + Math.round(age / 60) + "m";
                                            if (age < 86400) return "Edad: " + Math.round(age / 3600) + "h";
                                            return "Edad: " + Math.round(age / 86400) + "d";
                                        }
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Metrics Row (Health, Stability, Learning)
            Flow {
                width: parent.width
                spacing: 16

                // Organ Health
                GlassPanel {
                    width: pageScroll.availableWidth > 900 ? (pageScroll.availableWidth - 32) / 3 : pageScroll.availableWidth
                    fillColor: "#23313b"
                    strokeColor: borderSoft
                    implicitHeight: healthColumn.implicitHeight + 32

                    Column {
                        id: healthColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Salud del Organismo"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 18
                            font.bold: true
                        }

                        Label {
                            text: surfaceContract.organ_health ? surfaceContract.organ_health.overall_health || "UNRESOLVED" : "UNRESOLVED"
                            color: surfaceContract.organ_health && surfaceContract.organ_health.overall_health === "healthy" ? accentCyan : accentAmber
                            font.family: titleFontFamily
                            font.pixelSize: 32
                            font.bold: true
                        }

                        if (surfaceContract.organ_health && surfaceContract.organ_health.critical_findings_count !== undefined) {
                            Label {
                                text: "Hallazgos críticos: " + surfaceContract.organ_health.critical_findings_count
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        }

                        if (surfaceContract.organ_health && surfaceContract.organ_health.warning_findings_count !== undefined) {
                            Label {
                                text: "Hallazgos de advertencia: " + surfaceContract.organ_health.warning_findings_count
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        }

                        if (surfaceContract.organ_health && surfaceContract.organ_health.source) {
                            Label {
                                text: "Fuente: " + surfaceContract.organ_health.source
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                            }
                        }
                    }
                }

                // Stability
                GlassPanel {
                    width: pageScroll.availableWidth > 900 ? (pageScroll.availableWidth - 32) / 3 : pageScroll.availableWidth
                    fillColor: "#23313b"
                    strokeColor: borderSoft
                    implicitHeight: stabilityColumn.implicitHeight + 32

                    Column {
                        id: stabilityColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Estabilidad"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 18
                            font.bold: true
                        }

                        if (surfaceContract.stability && surfaceContract.stability.success_rate !== undefined) {
                            Label {
                                text: (surfaceContract.stability.success_rate * 100).toFixed(1) + "%"
                                color: surfaceContract.stability.success_rate >= 0.8 ? accentCyan : accentAmber
                                font.family: titleFontFamily
                                font.pixelSize: 32
                                font.bold: true
                            }
                            Label {
                                text: "Tasa de éxito"
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        } else {
                            Label {
                                text: "UNRESOLVED"
                                color: accentAmber
                                font.family: titleFontFamily
                                font.pixelSize: 24
                                font.bold: true
                            }
                        }

                        if (surfaceContract.stability && surfaceContract.stability.recent_runs_count !== undefined) {
                            Label {
                                text: "Ejecuciones recientes: " + surfaceContract.stability.recent_runs_count
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        }

                        if (surfaceContract.stability && surfaceContract.stability.source) {
                            Label {
                                text: "Fuente: " + surfaceContract.stability.source
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                            }
                        }
                    }
                }

                // Learning
                GlassPanel {
                    width: pageScroll.availableWidth > 900 ? (pageScroll.availableWidth - 32) / 3 : pageScroll.availableWidth
                    fillColor: "#23313b"
                    strokeColor: borderSoft
                    implicitHeight: learningColumn.implicitHeight + 32

                    Column {
                        id: learningColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Reutilización de Aprendizaje"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 18
                            font.bold: true
                        }

                        if (surfaceContract.learning && surfaceContract.learning.reuse_rate !== undefined) {
                            Label {
                                text: (surfaceContract.learning.reuse_rate * 100).toFixed(1) + "%"
                                color: surfaceContract.learning.reuse_rate >= 0.5 ? accentCyan : accentAmber
                                font.family: titleFontFamily
                                font.pixelSize: 32
                                font.bold: true
                            }
                            Label {
                                text: "Tasa de reutilización"
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        } else {
                            Label {
                                text: "UNRESOLVED"
                                color: accentAmber
                                font.family: titleFontFamily
                                font.pixelSize: 24
                                font.bold: true
                            }
                        }

                        if (surfaceContract.learning && surfaceContract.learning.total_runs !== undefined) {
                            Label {
                                text: "Total de ejecuciones: " + surfaceContract.learning.total_runs
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        }

                        if (surfaceContract.learning && surfaceContract.learning.reused_patterns_count !== undefined) {
                            Label {
                                text: "Patrones reutilizados: " + surfaceContract.learning.reused_patterns_count
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                            }
                        }

                        if (surfaceContract.learning && surfaceContract.learning.source) {
                            Label {
                                text: "Fuente: " + surfaceContract.learning.source
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                            }
                        }
                    }
                }
            }

            // Confidence Section
            GlassPanel {
                width: parent.width
                fillColor: "#22303a"
                strokeColor: borderSoft
                implicitHeight: confidenceColumn.implicitHeight + 32

                Column {
                    id: confidenceColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Confianza en Fuentes"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                        font.bold: true
                    }

                    if (surfaceContract.confidence && surfaceContract.confidence.overall_confidence !== undefined) {
                        Label {
                            text: (surfaceContract.confidence.overall_confidence * 100).toFixed(1) + "%"
                            color: surfaceContract.confidence.overall_confidence >= 0.7 ? accentCyan : accentAmber
                            font.family: titleFontFamily
                            font.pixelSize: 36
                            font.bold: true
                        }
                        Label {
                            text: "Confianza general"
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 13
                        }
                    } else {
                        Label {
                            text: "UNRESOLVED"
                            color: accentAmber
                            font.family: titleFontFamily
                            font.pixelSize: 28
                            font.bold: true
                        }
                    }

                    if (surfaceContract.confidence && surfaceContract.confidence.source) {
                        Label {
                            text: "Fuente: " + surfaceContract.confidence.source
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                        }
                    }
                }
            }

            // Evidence Sources Section
            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: evidenceColumn.implicitHeight + 32

                Column {
                    id: evidenceColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Fuentes de Evidencia"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                        font.bold: true
                    }

                    if (surfaceContract.evidence_sources && surfaceContract.evidence_sources.length > 0) {
                        Repeater {
                            model: surfaceContract.evidence_sources
                            delegate: Label {
                                text: "• " + modelData
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                                width: evidenceColumn.width
                                wrapMode: Label.WordWrap
                            }
                        }
                    } else {
                        Label {
                            text: "No hay fuentes de evidencia disponibles"
                            color: accentAmber
                            font.family: bodyFontFamily
                            font.pixelSize: 13
                        }
                    }
                }
            }

            // Unresolved Fields Section
            if (surfaceContract.unresolved_fields && surfaceContract.unresolved_fields.length > 0) {
                GlassPanel {
                    width: parent.width
                    fillColor: "#2d1a1a"
                    strokeColor: accentRed
                    implicitHeight: unresolvedColumn.implicitHeight + 32

                    Column {
                        id: unresolvedColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Campos No Resueltos"
                            color: accentRed
                            font.family: titleFontFamily
                            font.pixelSize: 20
                            font.bold: true
                        }

                        Repeater {
                            model: surfaceContract.unresolved_fields
                            delegate: Label {
                                text: "• " + modelData
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 13
                                width: unresolvedColumn.width
                                wrapMode: Label.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
