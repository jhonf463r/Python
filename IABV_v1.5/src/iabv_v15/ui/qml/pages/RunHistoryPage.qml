import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color borderSoft: "#42505d"
    readonly property string titleFontFamily: "Segoe UI"
    readonly property string bodyFontFamily: "Segoe UI"
    property var runsModel: runHistoryViewModel ? runHistoryViewModel.runs : []
    property var selectedRun: runHistoryViewModel ? runHistoryViewModel.selectedRun : ({})
    property var selectedDossier: runHistoryViewModel ? runHistoryViewModel.selectedDossier : ({})

    function modeLabel(value) {
        if (value === "local") return "local"
        if (value === "cloud") return "nube"
        if (value === "degraded") return "degradado"
        return value
    }

    GlassPanel {
        anchors.fill: parent
        fillColor: "#1c2630"
        strokeColor: borderSoft

        ScrollView {
            id: runScroll
            anchors.fill: parent
            anchors.margins: 18
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Column {
                width: runScroll.availableWidth
                spacing: 14
                RowLayout {
                    width: parent.width
                    Label {
                        text: "Historial de ejecuciones"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 22
                        Layout.fillWidth: true
                    }
                    AppButton {
                        text: "Actualizar"
                        accent: true
                        onClicked: if (runHistoryViewModel) runHistoryViewModel.refresh()
                    }
                }

                Label {
                    visible: runsModel.length === 0
                    text: "Aun no hay ejecuciones registradas. Las consultas por rol y los reportes locales apareceran aqui."
                    color: textSecondary
                    font.family: bodyFontFamily
                    font.pixelSize: 13
                    wrapMode: Label.WordWrap
                }

                Repeater {
                    model: runsModel
                    delegate: Rectangle {
                        width: runScroll.availableWidth
                        radius: 18
                        color: selectedRun.run_id === modelData.run_id ? "#314651" : "#2a3640"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: cardContent.implicitHeight + 24

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: if (runHistoryViewModel) runHistoryViewModel.selectRun(modelData.run_id)
                        }

                        Column {
                            id: cardContent
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 5
                            Label {
                                text: modelData.result.inferred_task
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                            Label {
                                text: modelData.result.summary || modelData.error_summary || "Sin respuesta visible."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                            Label {
                                text: "estado " + modelData.status + " | duracion " + modelData.duration_label + " | rol " + modelData.role_label + " | modelo " + modelData.model_label
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                            RowLayout {
                                width: parent.width
                                spacing: 6
                                Label {
                                    text: "planner " + modelData.planner_label + " | modo " + modeLabel(modelData.result.reasoning_mode) + " | dossier " + (modelData.incident_available ? "si" : "no")
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                    Layout.fillWidth: true
                                }
                                TruthStateBadge {
                                    truthState: modelData.truth_state || ""
                                }
                            }
                            Label {
                                visible: !!modelData.selected_worker_label || !!modelData.tool_selection_reason
                                text: (modelData.selected_worker_label ? "worker " + modelData.selected_worker_label + " | " : "") + "gate " + (modelData.gate_ran ? (modelData.gate_usable ? "usable (" + modelData.gate_available_count + ")" : "bloqueado") : "no ejecutado (" + (modelData.tool_selection_reason || "gate_not_ran") + ")") + (modelData.approval_required ? " | aprobacion requerida" : "")
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                            Label {
                                visible: !!modelData.route_reason
                                text: "ruta: " + (modelData.route_reason || "")
                                color: "#b0bec5"
                                font.family: bodyFontFamily
                                font.pixelSize: 10
                                wrapMode: Label.WordWrap
                                width: parent.width
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }
                            Label {
                                visible: modelData.unresolved_count > 0
                                text: "unresolved (" + modelData.unresolved_count + "): " + modelData.unresolved_summary
                                color: "#ffb74d"
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                            Label {
                                visible: !!modelData.dossier_summary
                                text: "dossier: " + modelData.dossier_summary
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: dossierCol.implicitHeight + 24

                    Column {
                        id: dossierCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6
                        Label {
                            text: "Dossier de la ejecucion seleccionada"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }
                        Label {
                            text: selectedDossier.title || "Selecciona una ejecucion para ver su dossier."
                            color: textPrimary
                            font.family: bodyFontFamily
                            font.pixelSize: 13
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                        Label {
                            text: selectedDossier.summary || ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                        Label {
                            visible: !!selectedDossier.next_action
                            text: "siguiente accion: " + selectedDossier.next_action
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                    }
                }
            }
        }
    }
}
