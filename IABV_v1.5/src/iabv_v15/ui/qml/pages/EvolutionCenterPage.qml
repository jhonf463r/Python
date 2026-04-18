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
    property var healthSnapshot: evolutionCenterViewModel ? evolutionCenterViewModel.healthSnapshot : ({})
    property var recentDossiers: evolutionCenterViewModel ? evolutionCenterViewModel.recentDossiers : []
    property var recentIncidents: evolutionCenterViewModel ? evolutionCenterViewModel.recentIncidents : []
    property var improvementBacklog: evolutionCenterViewModel ? evolutionCenterViewModel.improvementBacklog : []
    property var selectedDossier: evolutionCenterViewModel ? evolutionCenterViewModel.selectedDossier : ({})
    property var selectedIncident: evolutionCenterViewModel ? evolutionCenterViewModel.selectedIncident : ({})
    property var knownToolCards: evolutionCenterViewModel ? evolutionCenterViewModel.knownToolCards : []
    property var iaComparisons: evolutionCenterViewModel ? evolutionCenterViewModel.iaComparisons : []
    property var environmentSelfModel: evolutionCenterViewModel ? evolutionCenterViewModel.environmentSelfModel : ({})
    property var worldModel: evolutionCenterViewModel ? evolutionCenterViewModel.worldModel : ({})
    property string latestToolStatus: evolutionCenterViewModel ? evolutionCenterViewModel.latestToolStatus : ""
    property string incidentFilter: evolutionCenterViewModel ? evolutionCenterViewModel.incidentFilter : "all"
    property var statusCards: healthSnapshot.status_cards || []

    GlassPanel {
        anchors.fill: parent
        fillColor: "#1c2630"
        strokeColor: borderSoft

        ScrollView {
            id: evolutionScroll
            anchors.fill: parent
            anchors.margins: 18
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            Column {
                width: evolutionScroll.availableWidth
                spacing: 16

                RowLayout {
                    width: parent.width
                    spacing: 14

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Label {
                            text: "Centro Evolutivo"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 24
                            font.bold: true
                        }
                        Label {
                            text: evolutionCenterViewModel ? evolutionCenterViewModel.statusText : "Sin estado evolutivo."
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
                        onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.refresh()
                    }
                    AppButton {
                        text: "Ejecutar autodiagnostico"
                        onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.runDeepSelfCheck()
                    }
                }

                Rectangle {
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: compactSummary.implicitHeight + 24

                    Column {
                        id: compactSummary
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        Label {
                            text: "Pulso rapido del sistema"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        Flow {
                            width: parent.width
                            spacing: 10

                            Repeater {
                                model: statusCards
                                delegate: Rectangle {
                                    width: Math.max(150, (compactSummary.width - 20) / 3)
                                    height: 90
                                    radius: 14
                                    color: "#2a3640"
                                    border.width: 1
                                    border.color: borderSoft

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4

                                        Label {
                                            text: modelData.title
                                            color: textSecondary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 11
                                        }
                                        Label {
                                            text: modelData.value
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 24
                                            font.bold: true
                                        }
                                        Label {
                                            text: modelData.detail
                                            color: textSecondary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 10
                                            wrapMode: Label.WordWrap
                                            width: parent.width
                                            maximumLineCount: 2
                                            elide: Label.ElideRight
                                        }
                                    }
                                }
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
                    implicitHeight: toolsCol.implicitHeight + 24

                    Column {
                        id: toolsCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        Label {
                            text: "Herramientas conocidas"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 10

                            AppButton {
                                text: "Auditar base"
                                onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.auditBaseTools()
                            }

                            AppButton {
                                text: "Copiar estado"
                                enabled: latestToolStatus.length > 0
                                onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.copyLatestToolStatus()
                            }

                            Item {
                                Layout.fillWidth: true
                            }
                        }

                        TextArea {
                            width: parent.width
                            readOnly: true
                            wrapMode: TextArea.Wrap
                            text: latestToolStatus
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            selectByMouse: true
                            padding: 0
                            background: null
                        }

                        Label {
                            text: evolutionCenterViewModel ? evolutionCenterViewModel.clipboardNotice : ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: knownToolCards.length === 0
                            text: "Todavia no hay ToolCards registradas en esta sesion."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Repeater {
                            model: knownToolCards
                            delegate: Rectangle {
                                width: toolsCol.width
                                radius: 14
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: toolCardCol.implicitHeight + 20

                                Column {
                                    id: toolCardCol
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6

                                    RowLayout {
                                        width: parent.width
                                        spacing: 10

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            Label {
                                                text: modelData.title
                                                color: textPrimary
                                                font.family: titleFontFamily
                                                font.pixelSize: 14
                                            }
                                            Label {
                                                text: (modelData.tool_type || "n/d") + " | validacion " + (modelData.validation_status || "n/d") + " | disponible " + (modelData.available ? "si" : "no")
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                                Layout.fillWidth: true
                                            }
                                        }

                                        AppButton {
                                            text: "Sandbox"
                                            onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.sandboxToolCard(modelData.tool_id)
                                        }
                                    }

                                    Label {
                                        text: modelData.description || ""
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

                Rectangle {
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: worldModelCol.implicitHeight + 24

                    Column {
                        id: worldModelCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "World Model Operativo"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        Label {
                            text: "foco " + ((worldModel.focused_window && worldModel.focused_window.title) ? worldModel.focused_window.title : "sin foco confirmado")
                                  + " | red " + ((worldModel.network_status && worldModel.network_status.status) ? worldModel.network_status.status : "n/d")
                                  + " | confianza " + Number(worldModel.confidence || 0).toFixed(2)
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            text: "ventanas activas " + ((worldModel.active_windows || []).length)
                                  + " | herramientas observadas " + ((worldModel.tool_live_status || []).length)
                                  + " | procesos relevantes " + ((worldModel.background_processes || []).length)
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: (worldModel.detected_blocks || []).length > 0
                            text: "bloqueos: " + (worldModel.detected_blocks || []).join(", ")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: worldModel.inferred_state && (worldModel.inferred_state.deductions || []).length > 0
                            text: "deducciones: " + (worldModel.inferred_state.deductions || []).join(" | ")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: (worldModel.unresolved_fields || []).length > 0
                            text: "UNRESOLVED: " + (worldModel.unresolved_fields || []).join(", ")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Repeater {
                            model: worldModel.tool_live_status || []
                            delegate: Rectangle {
                                width: worldModelCol.width
                                radius: 14
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: worldToolCard.implicitHeight + 20

                                Column {
                                    id: worldToolCard
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4

                                    Label {
                                        text: (modelData.title || modelData.tool_id || "herramienta") + " -> " + (modelData.status || "n/d")
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 13
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }

                                    Label {
                                        text: "hilo " + (modelData.thread_status || "n/d")
                                              + " | mensajes " + (modelData.messages_status || "n/d")
                                              + " | sesion " + (modelData.session_status || "n/d")
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                    width: parent.width
                                    }

                                    Label {
                                        visible: !!(modelData.detail || "").length
                                        text: modelData.detail || ""
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

                Rectangle {
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: environmentCol.implicitHeight + 24

                    Column {
                        id: environmentCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Autoconciencia del entorno"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        Label {
                            text: "entorno " + (environmentSelfModel.environment_id || "sin id") + " | estado " + (environmentSelfModel.scan_status || "n/d") + " | conocido " + ((environmentSelfModel.known_environment || false) ? "si" : "no")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            text: "CPU " + (environmentSelfModel.hardware_profile && environmentSelfModel.hardware_profile.processor_name ? environmentSelfModel.hardware_profile.processor_name : "n/d")
                                  + " | RAM libre " + Number(((environmentSelfModel.hardware_profile && environmentSelfModel.hardware_profile.memory_free_bytes) || 0) / (1024 * 1024 * 1024)).toFixed(2) + " GB"
                                  + " | GPU " + (environmentSelfModel.hardware_profile && environmentSelfModel.hardware_profile.gpu_name ? environmentSelfModel.hardware_profile.gpu_name : "n/d")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            text: "IA local: " + (environmentSelfModel.ai_capacity && environmentSelfModel.ai_capacity.max_recommended_model ? environmentSelfModel.ai_capacity.max_recommended_model : "n/d")
                                  + " | herramientas listas " + ((environmentSelfModel.available_tools || []).length)
                                  + " | faltantes " + ((environmentSelfModel.missing_tools || []).length)
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: (environmentSelfModel.notifications || []).length > 0
                            text: "avisos: " + (environmentSelfModel.notifications || []).join(" | ")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Label {
                            visible: (environmentSelfModel.unresolved_fields || []).length > 0
                            text: "UNRESOLVED: " + (environmentSelfModel.unresolved_fields || []).join(", ")
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: iaTraceCol.implicitHeight + 24

                    Column {
                        id: iaTraceCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        Label {
                            text: "Comparacion entre IAs"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        Label {
                            visible: iaComparisons.length === 0
                            text: "Todavia no hay comparaciones consolidadas entre asistentes para mostrar."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }

                        Repeater {
                            model: iaComparisons
                            delegate: Rectangle {
                                width: iaTraceCol.width
                                radius: 14
                                color: "#2a3640"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: iaTraceCard.implicitHeight + 20

                                Column {
                                    id: iaTraceCard
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4

                                    Label {
                                        text: (modelData.subject_key || "general") + " -> " + (modelData.recommended_assistant_kind || "sin asistente") + " / " + (modelData.recommended_route || "sin ruta")
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 14
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        text: "config " + (modelData.recommended_config_signature || "base") + " | score " + Number(modelData.score || 0).toFixed(2) + " | confianza " + Number(modelData.confidence || 0).toFixed(2)
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        visible: (modelData.comparison_scope_keys || []).length > 0
                                        text: "scope: " + (modelData.comparison_scope_keys || []).join(", ")
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        visible: (modelData.winning_trace_ids || []).length > 0
                                        text: "trazas ganadoras: " + (modelData.winning_trace_ids || []).join(", ")
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

                RowLayout {
                    width: parent.width
                    spacing: 14
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 18
                        color: "#22313a"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: incidentsCol.implicitHeight + 24

                        Column {
                            id: incidentsCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Label {
                                text: "Incidentes invisibles recientes"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }

                            Flow {
                                width: parent.width
                                spacing: 8
                                AppButton { text: "Todos"; accent: incidentFilter === "all"; onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.setIncidentFilter("all") }
                                AppButton { text: "Captura"; accent: incidentFilter === "captura"; onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.setIncidentFilter("captura") }
                                AppButton { text: "Navegacion"; accent: incidentFilter === "navegacion"; onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.setIncidentFilter("navegacion") }
                                AppButton { text: "Finalizacion"; accent: incidentFilter === "finalizacion"; onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.setIncidentFilter("finalizacion") }
                                AppButton { text: "Replay"; accent: incidentFilter === "replay"; onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.setIncidentFilter("replay") }
                            }

                            Label {
                                visible: recentIncidents.length === 0
                                text: "No hay incidentes abiertos para este filtro. Cuando la maquina detecte algo raro, aparecera aqui con evidencia enlazada."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }

                            Repeater {
                                model: recentIncidents
                                delegate: Rectangle {
                                    width: incidentsCol.width
                                    radius: 14
                                    color: selectedIncident.incident_id === modelData.incident_id ? "#314651" : "#2a3640"
                                    border.width: 1
                                    border.color: borderSoft
                                    implicitHeight: incidentCard.implicitHeight + 20

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.selectIncident(modelData.incident_id)
                                    }

                                    Column {
                                        id: incidentCard
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4

                                        Label {
                                            text: modelData.incident_kind
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 14
                                            wrapMode: Label.WordWrap
                                            width: parent.width
                                        }
                                        Label {
                                            text: "estado " + modelData.status + " | severidad " + modelData.severity + " | sitio " + (modelData.site_id || "n/d")
                                            color: textSecondary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 11
                                            wrapMode: Label.WordWrap
                                            width: parent.width
                                        }
                                        Label {
                                            text: modelData.summary
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

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 18
                        color: "#22313a"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: dossiersCol.implicitHeight + 24

                        Column {
                            id: dossiersCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Label {
                                text: "Dossiers y parciales recientes"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }

                            Flow {
                                width: parent.width
                                spacing: 8
                                AppButton {
                                    text: "Ver evidencia relacionada"
                                    onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.viewIncidentEvidence()
                                }
                                AppButton {
                                    text: "Copiar paquete para Codex"
                                    onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.copyIncidentPacket()
                                }
                            }

                            Label {
                                visible: recentDossiers.length === 0
                                text: "Todavia no hay dossiers evolutivos recientes. Haz una consulta, una ensenanza o un replay para que se indexen aqui."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }

                            Repeater {
                                model: recentDossiers
                                delegate: Rectangle {
                                    width: dossiersCol.width
                                    radius: 14
                                    color: selectedDossier.dossier_id === modelData.dossier_id ? "#314651" : "#2a3640"
                                    border.width: 1
                                    border.color: borderSoft
                                    implicitHeight: dossierCard.implicitHeight + 20

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.selectDossier(modelData.dossier_id)
                                    }

                                    Column {
                                        id: dossierCard
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4

                                        Label {
                                            text: modelData.title
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 14
                                            wrapMode: Label.WordWrap
                                            width: parent.width
                                        }
                                        Label {
                                            text: "estado " + modelData.status + " | severidad " + modelData.severity + " | rol " + (modelData.detected_role || "n/d")
                                            color: textSecondary
                                            font.family: bodyFontFamily
                                            font.pixelSize: 11
                                            wrapMode: Label.WordWrap
                                            width: parent.width
                                        }
                                        Label {
                                            text: modelData.summary
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


                RowLayout {
                    width: parent.width
                    spacing: 14
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 18
                        color: "#22313a"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: backlogCol.implicitHeight + 24

                        Column {
                            id: backlogCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Label {
                                text: "Mejoras sugeridas priorizadas"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }
                            Repeater {
                                model: improvementBacklog
                                delegate: Label {
                                    width: backlogCol.width
                                    text: "- " + modelData.title + ": " + modelData.recommended_change
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                            }
                            Label {
                                visible: improvementBacklog.length === 0
                                text: "Todavia no hay mejoras priorizadas. Cuando el sistema encuentre patrones o incidentes repetidos, apareceran aqui."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                                width: parent.width
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 18
                        color: "#22313a"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: evidenceCol.implicitHeight + 24

                        Column {
                            id: evidenceCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            Label {
                                text: "Evidencia relacionada"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }
                            Label {
                                text: evolutionCenterViewModel ? evolutionCenterViewModel.evidencePreview : ""
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
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
                    implicitHeight: packetCol.implicitHeight + 24

                    Column {
                        id: packetCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        RowLayout {
                            width: parent.width
                            Label {
                                text: "Paquete verificable para Codex"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            AppButton {
                                text: "Copiar ultimo fallo"
                                onClicked: if (evolutionCenterViewModel) evolutionCenterViewModel.copyLatestFailurePacket()
                            }
                        }

                        TextArea {
                            width: parent.width
                            readOnly: true
                            wrapMode: TextArea.Wrap
                            text: evolutionCenterViewModel ? evolutionCenterViewModel.latestPacket : ""
                            color: textPrimary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            selectByMouse: true
                            background: Rectangle {
                                radius: 12
                                color: "#172028"
                                border.width: 1
                                border.color: borderSoft
                            }
                            implicitHeight: 220
                        }

                        Label {
                            text: evolutionCenterViewModel ? evolutionCenterViewModel.clipboardNotice : ""
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
