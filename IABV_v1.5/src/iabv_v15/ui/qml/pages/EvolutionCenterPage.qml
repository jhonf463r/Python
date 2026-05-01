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
    // Gap #107: "que necesita IABV del humano ahora".
    property var proactiveDashboard: evolutionCenterViewModel ? evolutionCenterViewModel.proactiveDashboard : ({})
    property string proactiveDashboardBrief: evolutionCenterViewModel ? evolutionCenterViewModel.proactiveDashboardBrief : ""
    property var proactiveEntries: proactiveDashboard.entries || []
    property int proactivePendingCount: proactiveDashboard.pending_attention_count || 0
    property int proactivePoliciesCount: proactiveDashboard.learned_policies_count || 0
    // F1.3: evidencia visual de la UI de IABV (UIScreenshotService).
    property var recentUiScreenshots: evolutionCenterViewModel ? evolutionCenterViewModel.recentUiScreenshots : []

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
                    AppButton {
                        text: "Publicar cambio como PR"
                        onClicked: publishPrDialog.open()
                    }
                }

                // F2.2: panel de estado de publicacion de PR. Muestra la ultima
                // salida de ``GitHubRemoteService.publish_branch_as_pr`` que
                // dispara el slot ``publishBranchAsPR``. No es una vista de
                // decision: solo refleja lo que el servicio reporto.
                Rectangle {
                    width: parent.width
                    radius: 14
                    color: "#1c2a33"
                    border.width: 1
                    border.color: borderSoft
                    implicitHeight: publishPrColumn.implicitHeight + 24
                    visible: evolutionCenterViewModel !== null

                    Column {
                        id: publishPrColumn
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6

                        Label {
                            text: "Publicacion de PR autonoma"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }
                        Label {
                            text: evolutionCenterViewModel ? evolutionCenterViewModel.publishPrStatus : ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                        Label {
                            id: publishPrEvidence
                            function _prResult() {
                                if (!evolutionCenterViewModel) return ({})
                                return evolutionCenterViewModel.publishPrResult || ({})
                            }
                            visible: {
                                var r = _prResult()
                                return r && (r.evidence_path || r.pr_url)
                            }
                            text: {
                                var r = _prResult()
                                if (!r) return ""
                                var parts = []
                                if (r.pr_url) parts.push("URL: " + r.pr_url)
                                if (r.evidence_path) parts.push("Evidencia: " + r.evidence_path)
                                return parts.join("\n")
                            }
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

                // Panel F1.3: evidencia visual reciente (UIScreenshotService).
                // Consume `recentUiScreenshots` del ViewModel. Se oculta cuando
                // no hay capturas para no ensuciar la UI. Solo lista metadatos:
                // el QML no decide rutas ni carga PNGs (AGENTS.md: el VM/QML no
                // inventa datos; el servicio persiste la foto en disco).
                Rectangle {
                    id: uiScreenshotsPanel
                    width: parent.width
                    radius: 18
                    color: "#22313a"
                    border.width: 1
                    border.color: borderSoft
                    visible: recentUiScreenshots && recentUiScreenshots.length > 0
                    implicitHeight: uiScreenshotsCol.implicitHeight + 24

                    Column {
                        id: uiScreenshotsCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: "Capturas UI recientes (" + (recentUiScreenshots ? recentUiScreenshots.length : 0) + ")"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }
                        Label {
                            text: "Evidencia visual persistida en data/evolution/ui_snapshots/."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 11
                            wrapMode: Label.WordWrap
                            width: parent.width
                        }
                        Repeater {
                            model: (recentUiScreenshots || []).slice(0, 5)
                            delegate: Rectangle {
                                width: uiScreenshotsCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: modelData.success ? borderSoft : "#c77a3a"
                                implicitHeight: uiShotEntryCol.implicitHeight + 16

                                Column {
                                    id: uiShotEntryCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 3

                                    Label {
                                        text: (modelData.source || "(sin source)") +
                                              "  \u2022  " +
                                              (modelData.width || 0) + "x" + (modelData.height || 0) +
                                              (modelData.success ? "" : "  \u2022  captura fallida")
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 13
                                        font.bold: true
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        text: modelData.path || ""
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        elide: Label.ElideMiddle
                                        width: parent.width
                                        visible: (modelData.path || "").length > 0
                                    }
                                    Label {
                                        text: {
                                            var scope = modelData.scope || {};
                                            var parts = [];
                                            for (var k in scope) {
                                                parts.push(k + "=" + scope[k]);
                                            }
                                            return parts.join("  \u2022  ");
                                        }
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                        visible: text.length > 0
                                    }
                                }
                            }
                        }
                    }
                }

                // Panel: "Que necesita IABV del humano ahora" (Gap #107).
                // Consume `proactiveDashboard` del ViewModel. Se oculta cuando
                // no hay pending ni politicas aprendidas (no ensucia UI).
                Rectangle {
                    id: proactivePanel
                    width: parent.width
                    radius: 18
                    color: proactivePendingCount > 0 ? "#3a2a2a" : "#22313a"
                    border.width: 1
                    border.color: proactivePendingCount > 0 ? "#b5651d" : borderSoft
                    visible: proactivePendingCount > 0 || proactivePoliciesCount > 0
                    implicitHeight: proactiveCol.implicitHeight + 24

                    Column {
                        id: proactiveCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Label {
                            text: proactivePendingCount > 0
                                ? ("IABV necesita del humano (" + proactivePendingCount + ")")
                                : "IABV no requiere atencion ahora"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                            font.bold: true
                        }
                        Label {
                            text: proactiveDashboardBrief
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            width: parent.width
                            visible: proactiveDashboardBrief.length > 0
                        }
                        Repeater {
                            model: proactiveEntries.slice(0, 5)
                            delegate: Rectangle {
                                width: proactiveCol.width
                                radius: 10
                                color: "#2a3640"
                                border.width: 1
                                border.color: modelData.severity === "critical"
                                    ? "#c77a3a"
                                    : (modelData.severity === "attention" ? "#b5a53a" : borderSoft)
                                implicitHeight: entryCol.implicitHeight + 16

                                Column {
                                    id: entryCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 3

                                    Label {
                                        text: modelData.title
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 13
                                        font.bold: true
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                    }
                                    Label {
                                        text: modelData.detail
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 11
                                        wrapMode: Label.WordWrap
                                        width: parent.width
                                        visible: modelData.detail.length > 0
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

                        RowLayout {
                            spacing: 8
                            Label {
                                text: "World Model Operativo"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }
                            TruthStateBadge { truthState: (worldModel.truthState || "") }
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

                        RowLayout {
                            spacing: 8
                            Label {
                                text: "Autoconciencia del entorno"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 16
                            }
                            TruthStateBadge { truthState: (environmentSelfModel.truthState || "") }
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

                        // ToolHealthPanel integrado (Task B)
                        ToolHealthPanel {
                            id: toolHealthPanel
                            width: parent.width
                            providers: evolutionCenterViewModel ? evolutionCenterViewModel.knownToolCards : []
                            onRotateToolRequested: {
                                if (evolutionCenterViewModel) evolutionCenterViewModel.rotateToolRequested()
                            }
                            onHelpRequested: {
                                if (evolutionCenterViewModel) evolutionCenterViewModel.helpRequested()
                            }
                            onRefreshRequested: {
                                if (evolutionCenterViewModel) evolutionCenterViewModel.refreshToolCards()
                            }
                        }

                        // BackgroundActivityChip integrado (Task B)
                        BackgroundActivityChip {
                            id: backgroundChip
                            anchors.horizontalCenter: parent.horizontalCenter
                            activityText: {
                                if (!evolutionCenterViewModel) return ""
                                var activity = evolutionCenterViewModel.backgroundActivity || {}
                                return activity.text || ""
                            }
                            progress: {
                                if (!evolutionCenterViewModel) return 0
                                var activity = evolutionCenterViewModel.backgroundActivity || {}
                                return activity.progress || 0
                            }
                            status: {
                                if (!evolutionCenterViewModel) return "idle"
                                var activity = evolutionCenterViewModel.backgroundActivity || {}
                                return activity.status || "idle"
                            }
                            visible: status !== "idle" && activityText !== ""
                        }
                    }
                }
            }
        }
    }

    // Dialogos evolutivos (Task B)
    CredentialPromptDialog {
        id: credentialDialog
        visible: false
        onCredentialProvided: function(payload) {
            if (evolutionCenterViewModel) evolutionCenterViewModel.onCredentialProvided(payload)
        }
        onDelegateToUser: function(payload) {
            if (evolutionCenterViewModel) evolutionCenterViewModel.onCredentialDelegated(payload)
        }
    }

    ClarificationDialog {
        id: clarificationDialog
        visible: false
        onClarificationResponse: function(payload) {
            if (evolutionCenterViewModel) evolutionCenterViewModel.onClarificationResponse(payload)
        }
    }

    // F2.2: dialogo modal para publicar una rama como PR via GitHubRemoteService.
    // No hace validacion de policy ni decide rutas: solo recoge los campos y
    // delega al slot del VM. La policy se evalua en el servicio.
    Dialog {
        id: publishPrDialog
        title: "Publicar cambio como PR"
        modal: true
        focus: true
        standardButtons: Dialog.Cancel | Dialog.Ok
        anchors.centerIn: parent
        width: Math.min(560, parent.width - 40)
        property alias branchText: publishPrBranch.text
        property alias titleText: publishPrTitle.text
        property alias bodyText: publishPrBody.text
        property alias baseText: publishPrBase.text
        property alias diffLinesText: publishPrDiff.text
        property alias draftChecked: publishPrDraft.checked

        contentItem: Column {
            spacing: 8
            width: parent.width

            Label {
                text: "Rama local (debe existir y estar pusheada en remote)"
                color: textSecondary
                font.pixelSize: 12
                wrapMode: Label.WordWrap
                width: parent.width
            }
            TextField {
                id: publishPrBranch
                placeholderText: "iabv-auto/mi-cambio"
                width: parent.width
            }
            Label { text: "Titulo del PR"; color: textSecondary; font.pixelSize: 12 }
            TextField {
                id: publishPrTitle
                placeholderText: "feat: ..."
                width: parent.width
            }
            Label { text: "Cuerpo (markdown, opcional)"; color: textSecondary; font.pixelSize: 12 }
            TextArea {
                id: publishPrBody
                width: parent.width
                height: 90
                wrapMode: TextArea.Wrap
            }
            Row {
                spacing: 10
                width: parent.width
                Column {
                    spacing: 4
                    Label { text: "Base"; color: textSecondary; font.pixelSize: 12 }
                    TextField {
                        id: publishPrBase
                        text: "main"
                        width: 140
                    }
                }
                Column {
                    spacing: 4
                    Label { text: "Diff lines (opcional)"; color: textSecondary; font.pixelSize: 12 }
                    TextField {
                        id: publishPrDiff
                        placeholderText: "0"
                        inputMethodHints: Qt.ImhDigitsOnly
                        width: 140
                    }
                }
                CheckBox {
                    id: publishPrDraft
                    text: "Draft"
                    checked: false
                }
            }
        }

        onAccepted: {
            if (!evolutionCenterViewModel) return
            var diff = parseInt(publishPrDiff.text, 10)
            if (isNaN(diff) || diff < 0) diff = 0
            evolutionCenterViewModel.publishBranchAsPR(
                publishPrBranch.text,
                publishPrTitle.text,
                publishPrBody.text,
                publishPrBase.text,
                diff,
                publishPrDraft.checked
            )
        }
    }

    MissingDependencyDialog {
        id: dependencyDialog
        visible: false
        onDependencyApproved: function(payload) {
            if (evolutionCenterViewModel) evolutionCenterViewModel.onDependencyApproved(payload)
        }
        onDependencyRejected: function(payload) {
            if (evolutionCenterViewModel) evolutionCenterViewModel.onDependencyRejected(payload)
        }
    }

    // Conexiones de señales del ViewModel (Task B)
    Connections {
        target: evolutionCenterViewModel
        function onCredentialPromptRequested(payload) {
            credentialDialog.domain = payload.domain || ""
            credentialDialog.reason = payload.reason || ""
            credentialDialog.usernameHint = payload.username_hint || ""
            credentialDialog.open()
        }
        function onClarificationRequested(payload) {
            clarificationDialog.requestId = payload.id || ""
            clarificationDialog.question = payload.question || ""
            clarificationDialog.options = payload.options || []
            clarificationDialog.context = payload.context || ""
            clarificationDialog.open()
        }
        function onMissingDependencyRequested(payload) {
            dependencyDialog.packageName = payload.package_name || ""
            dependencyDialog.manager = payload.manager || ""
            dependencyDialog.reason = payload.reason || ""
            dependencyDialog.open()
        }
    }
}
