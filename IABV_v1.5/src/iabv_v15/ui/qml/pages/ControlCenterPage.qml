import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color borderSoft: "#42505d"

    property bool liveDockExpanded: false
    property var chatMessagesModel: controlCenterViewModel ? controlCenterViewModel.chatMessages : []
    property bool advancedVisible: controlCenterViewModel ? controlCenterViewModel.advancedVisible : false
    property bool liveDockHydrated: liveDockExpanded
    property var liveProcessSummaryModel: liveDockHydrated && controlCenterViewModel ? controlCenterViewModel.liveProcessSummary : ({})
    property var liveWorkItemsModel: liveDockExpanded && controlCenterViewModel ? controlCenterViewModel.liveWorkItems : []
    property var assistantSessionCardsModel: liveDockExpanded && controlCenterViewModel ? controlCenterViewModel.assistantSessionCards : []
    property var autonomyTimelineModel: liveDockExpanded && controlCenterViewModel ? controlCenterViewModel.autonomyTimeline : []
    property var autonomyActivityModel: controlCenterViewModel ? controlCenterViewModel.autonomyActivity : ({})
    property bool compactPulseVisible: chatMessagesModel.length === 0 && !Boolean(autonomyActivityModel.visible)
    property var providerCardsModel: advancedVisible && controlCenterViewModel ? controlCenterViewModel.providerCards : []
    property var progressCardsModel: advancedVisible && controlCenterViewModel ? controlCenterViewModel.progressCards : []
    property var evolutionOverviewModel: (advancedVisible || compactPulseVisible) && controlCenterViewModel ? controlCenterViewModel.evolutionOverview : ({})
    property var evolutionAreaCardsModel: advancedVisible && controlCenterViewModel ? controlCenterViewModel.evolutionAreaCards : []
    property var evolutionBlockersModel: advancedVisible && controlCenterViewModel ? controlCenterViewModel.evolutionBlockers : []
    property string autonomyDockStatusValue: controlCenterViewModel ? controlCenterViewModel.autonomyDockStatus : "idle"
    property string autonomyDockLastResultValue: controlCenterViewModel ? controlCenterViewModel.autonomyDockLastResult : "idle"
    property string autonomyDockLastSummaryValue: controlCenterViewModel ? controlCenterViewModel.autonomyDockLastSummary : ""
    property var assistantActionButtonsModel: controlCenterViewModel ? controlCenterViewModel.assistantActionButtons : []
    property bool workingState: controlCenterViewModel ? controlCenterViewModel.working : false
    property bool canApproveStrategyValue: controlCenterViewModel ? controlCenterViewModel.canApproveStrategy : false
    property bool canApproveNextPhaseValue: controlCenterViewModel ? controlCenterViewModel.canApproveNextPhase : false
    property bool canSimulateValue: controlCenterViewModel ? controlCenterViewModel.canSimulate : false
    property bool canExecuteValue: controlCenterViewModel ? controlCenterViewModel.canExecute : false
    property bool canAbortValue: controlCenterViewModel ? controlCenterViewModel.canAbort : false
    property bool canApproveObservationValue: controlCenterViewModel ? controlCenterViewModel.canApproveObservation : false
    property bool approvalDialogVisibleValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogVisible : false
    property string routingModeLabelValue: controlCenterViewModel ? controlCenterViewModel.routingModeLabel : "Modo automatico"
    property string busyLabelText: controlCenterViewModel ? controlCenterViewModel.busyLabel : "Listo"
    property string clipboardNoticeValue: controlCenterViewModel ? controlCenterViewModel.clipboardNotice : ""
    property string assistantGuidanceModeValue: controlCenterViewModel ? controlCenterViewModel.assistantGuidanceMode : "idle"
    property string assistantGuidanceTextValue: controlCenterViewModel ? controlCenterViewModel.assistantGuidanceText : "Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex."
    property var externalEvidencePanelModel: controlCenterViewModel ? controlCenterViewModel.externalEvidencePanel : ({})
    property string approvalDialogTitleValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogTitle : "Aprobacion requerida"
    property string approvalDialogTextValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogText : ""
    property string recommendationTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.recommendationText : ""
    property string strategyTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.strategyText : ""
    property string diagnosticTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.diagnosticText : "Diagnostico pendiente."
    property string diagnosticTruthStateValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.diagnosticTruthState : ""
    property string repoBridgeTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.repoBridgeText : ""
    property string localStackTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.localStackText : ""
    property string developmentPacketValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.developmentPacket : ""
    property string adaptiveStatusTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveStatusText : "Sin sesion"
    property string adaptiveIntentTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveIntentText : ""
    property string adaptiveContextTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveContextText : ""
    property string adaptiveStrategyTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveStrategyText : ""
    property string adaptiveExecutionTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveExecutionText : ""
    property string adaptiveEvidenceTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveEvidenceText : ""
    property string adaptiveEvolutionTextValue: advancedVisible && controlCenterViewModel ? controlCenterViewModel.adaptiveEvolutionText : ""

    // ── Propiedades avanzadas del chat ──
    property int attachedFileCountValue: controlCenterViewModel ? controlCenterViewModel.attachedFileCount : 0
    property string liveStatusValue: controlCenterViewModel ? controlCenterViewModel.liveStatus : "idle"
    property var contextualSuggestionsModel: advancedVisible && controlCenterViewModel ? controlCenterViewModel.contextualSuggestions : []
    property var attachedFilesModel: controlCenterViewModel ? controlCenterViewModel.attachedFiles : []

    function localPathFromFileUrl(fileUrl) {
        var raw = String(fileUrl || "")
        if (raw.indexOf("file:///") === 0) {
            return decodeURIComponent(raw.substring(8))
        }
        if (raw.indexOf("file://") === 0) {
            return decodeURIComponent(raw.substring(7))
        }
        return decodeURIComponent(raw)
    }

    function fileNameFromPath(path) {
        var parts = String(path || "").split(/[\\/]/)
        return parts.length > 0 ? parts[parts.length - 1] : String(path || "")
    }

    FileDialog {
        id: attachmentDialog
        title: "Adjuntar archivo"
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "Documentos y datos (*.txt *.md *.pdf *.docx *.xlsx *.csv *.json *.py *.js *.ts *.qml *.png *.jpg *.jpeg)",
            "Todos los archivos (*)"
        ]
        onAccepted: {
            if (!controlCenterViewModel) return
            var selected = selectedFiles || []
            for (var i = 0; i < selected.length; i++) {
                var path = localPathFromFileUrl(selected[i])
                if (path.length > 0) {
                    controlCenterViewModel.attachFile(fileNameFromPath(path), path, 0, "application/octet-stream")
                }
            }
        }
    }

    Timer {
        id: autonomyDockTimer
        interval: 5000
        repeat: true
        running: liveDockExpanded && Boolean(controlCenterViewModel) && !workingState && autonomyDockStatusValue !== "refreshing" && (
            Boolean(autonomyActivityModel.visible)
            || (liveProcessSummaryModel.status || "") === "awaiting_response"
            || (liveProcessSummaryModel.status || "") === "active"
        )
        onTriggered: if (controlCenterViewModel) controlCenterViewModel.refreshAutonomyDock()
    }

    function capabilityColor(status) {
        if (status === "ready" || status === "ready_with_approval")
            return "#8ccf8b";
        if (status === "partial")
            return "#d9b15f";
        if (status === "blocked")
            return "#cf7e7e";
        return textSecondary;
    }

    function evolutionStatusColor(status) {
        if (status === "active")
            return "#8ccf8b";
        if (status === "awaiting_response" || status === "warning")
            return "#d9b15f";
        if (status === "blocked" || status === "failed")
            return "#cf7e7e";
        return textSecondary;
    }

    function pctLabel(value) {
        var numeric = Number(value || 0);
        if (!isFinite(numeric))
            numeric = 0;
        return Math.max(0, Math.min(100, Math.round(numeric)));
    }

    Popup {
        id: approvalPopup
        parent: root
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        visible: approvalDialogVisibleValue
        width: Math.min(root.width - 40, 760)
        x: Math.max(20, (root.width - width) / 2)
        y: 28
        padding: 0
        onClosed: if (controlCenterViewModel) controlCenterViewModel.dismissApprovalDialog()

        background: Rectangle {
            radius: 24
            color: "#17212a"
            border.width: 1
            border.color: borderSoft
        }

        contentItem: Column {
            width: approvalPopup.width
            spacing: 12
            padding: 20

            Label { text: approvalDialogTitleValue; color: textPrimary; font.pixelSize: 22; font.family: "Segoe UI" }
            Label {
                width: parent.width
                text: "Puedes aprobar directo desde aqui o escribirlo en el chat."
                color: textSecondary
                wrapMode: Label.WordWrap
                font.pixelSize: 12
                font.family: "Segoe UI"
            }
            AppTextArea { width: parent.width; readOnly: true; text: approvalDialogTextValue; implicitHeight: 180 }
            Flow {
                width: parent.width
                spacing: 10
                AppButton { visible: canApproveObservationValue; text: "Permitir observacion"; enabled: canApproveObservationValue; accent: true; onClicked: { if (controlCenterViewModel) controlCenterViewModel.applySuggestedAction("approve_observation_permission"); approvalPopup.close(); } }
                AppButton { visible: canApproveStrategyValue; text: "Aprobar estrategia"; enabled: canApproveStrategyValue; accent: true; onClicked: { if (controlCenterViewModel) controlCenterViewModel.approveStrategy(); approvalPopup.close(); } }
                AppButton { visible: canApproveNextPhaseValue; text: "Aprobar fase siguiente"; enabled: canApproveNextPhaseValue; accent: true; onClicked: { if (controlCenterViewModel) controlCenterViewModel.approveNextPhase(); approvalPopup.close(); } }
                AppButton { visible: canSimulateValue; text: "Simular"; enabled: canSimulateValue; onClicked: { if (controlCenterViewModel) controlCenterViewModel.simulateAdaptive(); approvalPopup.close(); } }
                AppButton { visible: canExecuteValue; text: "Ejecutar ahora"; enabled: canExecuteValue; accent: true; onClicked: { if (controlCenterViewModel) controlCenterViewModel.executeAdaptive(); approvalPopup.close(); } }
                AppButton { visible: canAbortValue; text: "Abortar"; enabled: canAbortValue; onClicked: { if (controlCenterViewModel) controlCenterViewModel.abortAdaptive(); approvalPopup.close(); } }
                AppButton { text: "Cerrar aviso"; onClicked: approvalPopup.close() }
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            width: parent.width
            spacing: 16

            GlassPanel {
                width: parent.width
                visible: compactPulseVisible
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: evolutionCompactCol.implicitHeight + 34

                Column {
                    id: evolutionCompactCol
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10

                    Label { text: "Pulso evolutivo"; color: textPrimary; font.pixelSize: 20; font.family: "Segoe UI" }
                    Label {
                        width: evolutionCompactCol.width
                        text: evolutionOverviewModel.summary || "Todavia no hay un pulso evolutivo consolidado."
                        color: textSecondary
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                        font.family: "Segoe UI"
                    }
                    Label {
                        width: evolutionCompactCol.width
                        text: "Estado: " + (evolutionOverviewModel.status || "idle") + " | Tendencia: " + (evolutionOverviewModel.trend || "sin base")
                        color: evolutionStatusColor(evolutionOverviewModel.status || "idle")
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                        font.family: "Segoe UI"
                    }
                    Label {
                        width: evolutionCompactCol.width
                        text: "Ultimo experimento o evaluacion: " + (evolutionOverviewModel.latest_experiment || "Sin evaluaciones recientes.")
                        color: textSecondary
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                        font.family: "Segoe UI"
                    }
                }
            }

            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: chatCol.implicitHeight + 34

                Column {
                    id: chatCol
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label { text: "Chat operativo"; color: textPrimary; font.pixelSize: 22; font.family: "Segoe UI" }
                    RowLayout {
                        width: chatCol.width
                        spacing: 10
                        Label {
                            Layout.fillWidth: true
                            text: busyLabelText
                            color: textSecondary
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                            font.family: "Segoe UI"
                        }
                        AppButton { text: advancedVisible ? "Ocultar avanzado" : "Mostrar avanzado"; onClicked: if (controlCenterViewModel) controlCenterViewModel.toggleAdvanced() }
                    }
                    Label {
                        width: chatCol.width
                        text: "Puedes seleccionar texto del chat con el cursor. Tambien puedes escribir mostrar avanzado, revisar stack, aprobar estrategia, simular, ejecutar ahora o abortar."
                        color: textSecondary
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                        font.family: "Segoe UI"
                    }
                    ListView {
                        id: chatListView
                        width: chatCol.width
                        height: 300
                        clip: true
                        spacing: 10
                        model: chatMessagesModel
                        reuseItems: true
                        cacheBuffer: 480
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: ChatMessageDelegate {
                            width: chatListView.width
                            onCopyRequested: function(text) {
                                if (controlCenterViewModel) controlCenterViewModel.copyToClipboard(text)
                            }
                            onDownloadRequested: function(text, filename) {
                                if (controlCenterViewModel) controlCenterViewModel.downloadChat(text, filename)
                            }
                            onApplyCodeRequested: function(code, language) {
                                if (controlCenterViewModel) controlCenterViewModel.applyCode(code, language)
                            }
                            onActionRequested: function(actionId, actionData) {
                                if (controlCenterViewModel) controlCenterViewModel.handleSuggestionAction(actionId, actionData.label || "")
                            }
                            onAttachmentClicked: function(path, name) {
                                console.log("Attachment clicked:", path, name)
                            }
                        }

                        onCountChanged: positionViewAtEnd()
                        Component.onCompleted: positionViewAtEnd()
                    }

                    Rectangle {
                        width: chatCol.width
                        visible: assistantGuidanceModeValue !== "idle" || assistantActionButtonsModel.length > 0
                        radius: 16
                        color: "#17212a"
                        border.width: 1
                        border.color: assistantGuidanceModeValue === "need_approval" ? "#d9b15f" : (assistantGuidanceModeValue === "need_codex_fix" ? "#cf7e7e" : "#315c6e")
                        implicitHeight: guidanceCol.implicitHeight + 20

                        Column {
                            id: guidanceCol
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Label { text: "Siguiente gesto sugerido"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                            Label {
                                width: guidanceCol.width
                                text: assistantGuidanceTextValue
                                color: textSecondary
                                wrapMode: Label.WordWrap
                                font.pixelSize: 12
                                font.family: "Segoe UI"
                            }
                            Flow {
                                width: guidanceCol.width
                                spacing: 10
                                Repeater {
                                    model: assistantActionButtonsModel
                                    delegate: AppButton {
                                        text: modelData.label
                                        accent: index === 0
                                        onClicked: if (controlCenterViewModel) controlCenterViewModel.applySuggestedAction(modelData.action)
                                    }
                                }
                            }
                        }
                    }

                    // ── Toolbar avanzado del chat ──
                    Rectangle {
                        width: chatCol.width
                        visible: Boolean(externalEvidencePanelModel.visible)
                        radius: 10
                        color: "#141e26"
                        border.width: 1
                        border.color: "#4f6d7a"
                        implicitHeight: externalEvidenceCol.implicitHeight + 20

                        Column {
                            id: externalEvidenceCol
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Label {
                                width: externalEvidenceCol.width
                                text: externalEvidencePanelModel.title || "Evidencia externa"
                                color: textPrimary
                                font.pixelSize: 14
                                font.family: "Segoe UI"
                                wrapMode: Label.WordWrap
                            }
                            Label {
                                width: externalEvidenceCol.width
                                text: "Estado: " + (externalEvidencePanelModel.status || "unresolved")
                                      + " | asistente: " + (externalEvidencePanelModel.assistant || "sin confirmar")
                                      + " | interaction_id: " + (externalEvidencePanelModel.interaction_id || "sin id")
                                color: textSecondary
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                wrapMode: Label.WordWrap
                            }
                            Flow {
                                width: externalEvidenceCol.width
                                spacing: 6
                                Repeater {
                                    model: externalEvidencePanelModel.phases || []
                                    delegate: Rectangle {
                                        radius: 6
                                        color: "#1b2a34"
                                        border.width: 1
                                        border.color: "#315c6e"
                                        implicitWidth: phaseLabel.implicitWidth + 16
                                        implicitHeight: phaseLabel.implicitHeight + 10
                                        Label {
                                            id: phaseLabel
                                            anchors.centerIn: parent
                                            text: (modelData.label || "")
                                                  + (modelData.detail ? " | " + modelData.detail : "")
                                            color: textSecondary
                                            font.pixelSize: 10
                                            font.family: "Segoe UI"
                                        }
                                    }
                                }
                            }
                            Repeater {
                                model: externalEvidencePanelModel.metadata || []
                                delegate: Label {
                                    width: externalEvidenceCol.width
                                    text: (modelData.key || "") + ": " + (modelData.value || "")
                                    color: textSecondary
                                    font.pixelSize: 11
                                    font.family: "Segoe UI"
                                    wrapMode: Label.WordWrap
                                }
                            }
                            Repeater {
                                model: externalEvidencePanelModel.visual_evidence || []
                                delegate: Column {
                                    width: externalEvidenceCol.width
                                    spacing: 4
                                    Label {
                                        width: parent.width
                                        text: (modelData.label || "Evidencia visual")
                                              + (modelData.detail ? " | " + modelData.detail : "")
                                        color: textSecondary
                                        font.pixelSize: 11
                                        font.family: "Segoe UI"
                                        wrapMode: Label.WordWrap
                                    }
                                    Label {
                                        width: parent.width
                                        visible: Boolean(modelData.semantic_summary)
                                        text: "Lectura: " + (((modelData.semantic_summary || ({})).state_hypothesis) || "sin lectura")
                                              + " | confianza=" + (((modelData.semantic_summary || ({})).confidence) || 0)
                                              + " | labels=" + ((((modelData.semantic_summary || ({})).labels) || []).join(", "))
                                        color: "#9fd0ff"
                                        font.pixelSize: 10
                                        font.family: "Segoe UI"
                                        wrapMode: Label.WordWrap
                                    }
                                    Rectangle {
                                        width: parent.width
                                        height: 170
                                        radius: 8
                                        color: "#0f171d"
                                        border.width: 1
                                        border.color: modelData.permission_granted ? "#3d8f5c" : "#7a5e2b"
                                        clip: true
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            source: modelData.image_url || ""
                                            fillMode: Image.PreserveAspectFit
                                            asynchronous: true
                                            cache: false
                                        }
                                    }
                                    Label {
                                        width: parent.width
                                        text: modelData.path || ""
                                        color: mutedText
                                        font.pixelSize: 10
                                        font.family: "Consolas"
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                            }
                            Label {
                                width: externalEvidenceCol.width
                                text: externalEvidencePanelModel.user_help || ""
                                visible: Boolean(externalEvidencePanelModel.user_help)
                                color: "#d9b15f"
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                wrapMode: Label.WordWrap
                            }
                            Flow {
                                width: externalEvidenceCol.width
                                spacing: 8
                                visible: (externalEvidencePanelModel.actions || []).length > 0
                                Repeater {
                                    model: externalEvidencePanelModel.actions || []
                                    delegate: AppButton {
                                        text: modelData.label || modelData.action || "Accion"
                                        accent: index === 0
                                        onClicked: if (controlCenterViewModel) controlCenterViewModel.applySuggestedAction(modelData.action)
                                    }
                                }
                            }
                        }
                    }

                    Loader {
                        width: chatCol.width
                        active: true
                        visible: true
                        sourceComponent: chatToolbarComponent
                    }

                    Rectangle {
                        width: chatCol.width
                        visible: attachedFilesModel.length > 0
                        radius: 8
                        color: "#121b22"
                        border.width: 1
                        border.color: "#2e4453"
                        implicitHeight: attachedFilesCol.implicitHeight + 18

                        Column {
                            id: attachedFilesCol
                            anchors.fill: parent
                            anchors.margins: 9
                            spacing: 6

                            Label {
                                width: attachedFilesCol.width
                                text: attachedFilesModel.length + " archivo(s) adjunto(s) para el siguiente mensaje"
                                color: textSecondary
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                                wrapMode: Label.WordWrap
                            }
                            Flow {
                                width: attachedFilesCol.width
                                spacing: 6
                                Repeater {
                                    model: attachedFilesModel
                                    delegate: Rectangle {
                                        radius: 6
                                        color: "#1b2a34"
                                        border.width: 1
                                        border.color: "#315c6e"
                                        implicitWidth: Math.min(attachedFilesCol.width, fileChipRow.implicitWidth + 16)
                                        implicitHeight: fileChipRow.implicitHeight + 8

                                        Row {
                                            id: fileChipRow
                                            anchors.centerIn: parent
                                            spacing: 6
                                            Label {
                                                text: modelData.name || fileNameFromPath(modelData.path || "")
                                                color: textSecondary
                                                font.pixelSize: 10
                                                font.family: "Segoe UI"
                                                elide: Label.ElideRight
                                                width: Math.min(260, attachedFilesCol.width - 50)
                                            }
                                            ToolButton {
                                                width: 18
                                                height: 18
                                                text: "x"
                                                onClicked: if (controlCenterViewModel) controlCenterViewModel.detachFile(modelData.path || "")
                                                ToolTip.visible: hovered
                                                ToolTip.text: "Quitar adjunto"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── Panel de sugerencias contextuales ──
                    Loader {
                        id: suggestionsPanelLoader
                        width: chatCol.width
                        active: advancedVisible && contextualSuggestionsModel.length > 0
                        visible: active
                        sourceComponent: contextualSuggestionsComponent
                    }

                    AppTextArea { id: chatInput; width: chatCol.width; implicitHeight: 92; selectByMouse: true; placeholderText: "Describe la tarea cotidiana que quieres resolver o automatizar por fases..." }
                    Flow {
                        width: chatCol.width
                        spacing: 10
                        AppButton {
                            text: workingState ? "Consultando..." : "Enviar"
                            accent: true
                            enabled: !workingState
                            onClicked: {
                                if (controlCenterViewModel) {
                                    var outgoing = chatInput.text.trim();
                                    if (outgoing.length > 0) {
                                        controlCenterViewModel.sendChat(outgoing);
                                        chatInput.text = "";
                                        suggestionsPanelLoader.visible = false;
                                    }
                                }
                            }
                        }
                        AppButton { text: "Automatico"; onClicked: if (controlCenterViewModel) controlCenterViewModel.setRole("auto") }
                        Label { text: routingModeLabelValue || "Modo automatico"; color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; verticalAlignment: Label.AlignVCenter }
                    }
                    Label { text: clipboardNoticeValue; color: textSecondary; font.pixelSize: 11; wrapMode: Label.WordWrap; font.family: "Segoe UI" }

                    GlassPanel {
                        width: chatCol.width
                        fillColor: "#162028"
                        strokeColor: borderSoft
                        implicitHeight: liveDockCol.implicitHeight + 28

                        Column {
                            id: liveDockCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            RowLayout {
                                width: liveDockCol.width
                                spacing: 10
                                Label { Layout.fillWidth: true; text: "Dock vivo de autonomia"; color: textPrimary; font.pixelSize: 18; font.family: "Segoe UI" }
                                AppButton { text: liveDockExpanded ? "Compactar" : "Expandir"; onClicked: liveDockExpanded = !liveDockExpanded }
                                AppButton {
                                    text: autonomyDockStatusValue === "refreshing" ? "Actualizando..." : "Refrescar"
                                    enabled: !workingState && autonomyDockStatusValue !== "refreshing"
                                    onClicked: if (controlCenterViewModel) controlCenterViewModel.refreshAutonomyDockFromUser()
                                }
                            }

                            Label {
                                width: liveDockCol.width
                                text: liveDockExpanded ? "Cargando detalle vivo bajo demanda." : "Compactado para proteger la ventana. Pulsa Expandir para ver Actividad autonoma, Trabajo vivo y Timeline."
                                color: textSecondary
                                wrapMode: Label.WordWrap
                                font.pixelSize: 12
                                font.family: "Segoe UI"
                            }

                            Loader {
                                id: liveDockDetailsLoader
                                width: liveDockCol.width
                                active: liveDockExpanded
                                visible: liveDockExpanded
                                sourceComponent: liveDockDetailsComponent
                            }
                        }
                    }
                }
            }

            Loader {
                width: parent.width
                active: advancedVisible
                visible: advancedVisible
                sourceComponent: advancedPanelComponent
            }

            Component {
                id: chatToolbarComponent

                ChatToolbar {
                    id: chatToolbar
                    width: chatCol.width
                    toolCount: providerCardsModel.length
                    activeProvider: routingModeLabelValue.toLowerCase().indexOf("chatgpt") >= 0 ? "chatgpt" : (routingModeLabelValue.toLowerCase().indexOf("claude") >= 0 ? "claude" : (routingModeLabelValue.toLowerCase().indexOf("devin") >= 0 ? "devin" : (routingModeLabelValue.toLowerCase().indexOf("ollama") >= 0 ? "ollama" : "auto")))
                    codeMode: false
                    canAttach: true
                    attachedCount: attachedFileCountValue
                    systemStatus: liveStatusValue === "idle" ? "idle" : (liveStatusValue === "error" ? "error" : "processing")
                    onAttachClicked: {
                        attachmentDialog.open()
                    }
                    onClearAttachments: {
                        if (controlCenterViewModel) controlCenterViewModel.clearAttachedFiles()
                    }
                    onCodeModeToggled: console.log("Code mode toggled")
                    onSearchClicked: console.log("Search clicked")
                    onProviderSwitchClicked: {
                        if (controlCenterViewModel) controlCenterViewModel.setRole("auto")
                    }
                    onKeyInputRequested: {
                        if (controlCenterViewModel) controlCenterViewModel.sendChat("ingresar clave")
                    }
                    onSearchQueryChanged: {
                        if (controlCenterViewModel) controlCenterViewModel.searchChatHistory(chatToolbar.searchQuery)
                    }
                }
            }

            Component {
                id: contextualSuggestionsComponent

                ContextualSuggestionsPanel {
                    width: chatCol.width
                    suggestions: contextualSuggestionsModel
                    onSuggestionClicked: function(action, text) {
                        if (controlCenterViewModel) controlCenterViewModel.handleSuggestionAction(action, text)
                    }
                    onDismissed: suggestionsPanelLoader.visible = false
                }
            }

            Component {
                id: liveDockDetailsComponent

                Column {
                    width: liveDockDetailsLoader.width
                    spacing: 10

                    Label {
                        width: parent.width
                        visible: Boolean(autonomyDockLastSummaryValue)
                        text: autonomyDockLastSummaryValue
                        color: autonomyDockLastResultValue === "failed" ? "#cf7e7e" : (autonomyDockLastResultValue === "changed" ? "#8ccf8b" : textSecondary)
                        wrapMode: Label.WordWrap
                        font.pixelSize: 11
                        font.family: "Segoe UI"
                    }
                    Label {
                        width: parent.width
                        text: liveProcessSummaryModel.summary || "Todavia no hay trabajo autonomo consolidado."
                        color: textSecondary
                        wrapMode: Label.WordWrap
                        font.pixelSize: 12
                        font.family: "Segoe UI"
                    }
                    Flow {
                        width: parent.width
                        spacing: 10
                        StatusPill {
                            label: "Etapa: " + (liveProcessSummaryModel.stage || "sin actividad")
                            accentColor: evolutionStatusColor(liveProcessSummaryModel.status || "idle")
                            pulsing: (liveProcessSummaryModel.status || "") === "awaiting_response"
                            minPillWidth: 170
                            maxPillWidth: 340
                        }
                        StatusPill {
                            label: "Progreso: " + pctLabel(liveProcessSummaryModel.progress_pct) + "%"
                            accentColor: "#3e7b63"
                            minPillWidth: 150
                            maxPillWidth: 220
                        }
                    }
                    Label { width: parent.width; text: "Objetivo: " + (liveProcessSummaryModel.goal_title || "sin objetivo"); color: textPrimary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }
                    Label { width: parent.width; text: "Paso actual: " + (liveProcessSummaryModel.current_step || "sin actividad"); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                    Label { width: parent.width; text: "Actividad autonoma"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                    Label { width: parent.width; text: autonomyActivityModel.detail || "Sin actividad visible."; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                    Label { width: parent.width; visible: Boolean(autonomyActivityModel.next_step); text: "Siguiente paso: " + (autonomyActivityModel.next_step || ""); color: textPrimary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                    Label { width: parent.width; visible: Boolean(autonomyActivityModel.learning_note); text: "Aprendizaje: " + (autonomyActivityModel.learning_note || ""); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                    Label { width: parent.width; text: "Trabajo vivo y Timeline se cargan bajo demanda para evitar congelamientos del usuario."; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                    Flow {
                        width: parent.width
                        spacing: 8
                        visible: Boolean(liveProcessSummaryModel.task_id)
                        AppButton { text: "Vas bien"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(liveProcessSummaryModel.task_id || "", "vas bien") }
                        AppButton { text: "Corrige ruta"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(liveProcessSummaryModel.task_id || "", "corrige ruta") }
                        AppButton { text: "No uses este chat"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(liveProcessSummaryModel.task_id || "", "no uses este chat") }
                        AppButton { text: "Aprendizaje util"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(liveProcessSummaryModel.task_id || "", "aprendizaje util") }
                        AppButton { text: "Aprendizaje incorrecto"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(liveProcessSummaryModel.task_id || "", "aprendizaje incorrecto") }
                    }
                }
            }

            Component {
                id: advancedPanelComponent

                Column {
                width: root.width
                spacing: 16

                GlassPanel {
                    width: parent.width
                    fillColor: "#1c2630"
                    strokeColor: borderSoft
                    implicitHeight: advancedCol.implicitHeight + 34

                    Column {
                        id: advancedCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label { text: "Panel avanzado"; color: textPrimary; font.pixelSize: 20; font.family: "Segoe UI" }
                        Label { text: adaptiveStatusTextValue; color: textSecondary; font.pixelSize: 12; font.family: "Segoe UI"; wrapMode: Label.WordWrap }

                        Flow {
                            width: advancedCol.width
                            spacing: 16

                            GlassPanel {
                                width: advancedCol.width > 1200 ? advancedCol.width * 0.5 - 8 : advancedCol.width
                                fillColor: "#162028"
                                strokeColor: borderSoft
                                implicitHeight: leftAdvancedCol.implicitHeight + 24

                                Column {
                                    id: leftAdvancedCol
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    Label { text: "Intento"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveIntentTextValue; implicitHeight: 120 }
                                    Label { text: "Contexto"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveContextTextValue; implicitHeight: 120 }
                                    Label { text: "Recomendacion"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: recommendationTextValue; implicitHeight: 90 }
                                    RowLayout {
                                        spacing: 8
                                        Label { text: "Diagnostico"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                        TruthStateBadge { truthState: diagnosticTruthStateValue }
                                    }
                                    AppTextArea { width: parent.width; readOnly: true; text: diagnosticTextValue; implicitHeight: 120 }
                                }
                            }

                            GlassPanel {
                                width: advancedCol.width > 1200 ? advancedCol.width * 0.5 - 8 : advancedCol.width
                                fillColor: "#162028"
                                strokeColor: borderSoft
                                implicitHeight: rightAdvancedCol.implicitHeight + 24

                                Column {
                                    id: rightAdvancedCol
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    Label { text: "Estrategia"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveStrategyTextValue || strategyTextValue; implicitHeight: 120 }
                                    Label { text: "Ejecucion"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveExecutionTextValue; implicitHeight: 120 }
                                    Label { text: "Evidencia"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveEvidenceTextValue; implicitHeight: 90 }
                                    Label { text: "Evolutivo"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                                    AppTextArea { width: parent.width; readOnly: true; text: adaptiveEvolutionTextValue; implicitHeight: 90 }
                                }
                            }
                        }

                        Label { text: "Aprobaciones"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                        Flow {
                            width: advancedCol.width
                            spacing: 10
                            AppButton { visible: canApproveStrategyValue; text: "Aprobar estrategia"; accent: true; onClicked: if (controlCenterViewModel) controlCenterViewModel.approveStrategy() }
                            AppButton { visible: canApproveNextPhaseValue; text: "Aprobar fase siguiente"; accent: true; onClicked: if (controlCenterViewModel) controlCenterViewModel.approveNextPhase() }
                            AppButton { visible: canSimulateValue; text: "Simular"; onClicked: if (controlCenterViewModel) controlCenterViewModel.simulateAdaptive() }
                            AppButton { visible: canExecuteValue; text: "Ejecutar ahora"; accent: true; onClicked: if (controlCenterViewModel) controlCenterViewModel.executeAdaptive() }
                            AppButton { visible: canAbortValue; text: "Abortar"; onClicked: if (controlCenterViewModel) controlCenterViewModel.abortAdaptive() }
                        }
                    }
                }

                GlassPanel {
                    width: parent.width
                    fillColor: "#1c2630"
                    strokeColor: borderSoft
                    implicitHeight: evolutionCol.implicitHeight + 34

                    Column {
                        id: evolutionCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10

                        Label { text: "Panel de evolucion"; color: textPrimary; font.pixelSize: 20; font.family: "Segoe UI" }
                        Label { width: parent.width; text: evolutionOverviewModel.summary || "Sin resumen evolutivo consolidado."; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }
                        Label { width: parent.width; text: "Ultimo experimento o evaluacion: " + (evolutionOverviewModel.latest_experiment || "Sin experimentos recientes."); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }

                        Repeater {
                            model: evolutionAreaCardsModel
                            delegate: Rectangle {
                                width: evolutionCol.width
                                radius: 12
                                color: "#162028"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: evolutionCardCol.implicitHeight + 16

                                Column {
                                    id: evolutionCardCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4
                                    Label { width: parent.width; text: modelData.title + " | " + (modelData.status || "idle") + " | " + (modelData.trend || "sin base"); color: textPrimary; font.pixelSize: 12; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                    Label { width: parent.width; text: modelData.summary || "Sin resumen."; color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                    Label { visible: Boolean(modelData.detail); width: parent.width; text: modelData.detail || ""; color: textSecondary; font.pixelSize: 10; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                }
                            }
                        }

                        Label { text: "Bloqueos e intervencion humana"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                        Repeater {
                            model: evolutionBlockersModel
                            delegate: Label {
                                width: evolutionCol.width
                                text: modelData.title + ": " + modelData.detail
                                color: capabilityColor(modelData.status || "blocked")
                                wrapMode: Label.WordWrap
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                            }
                        }
                    }
                }

                GlassPanel {
                    width: parent.width
                    fillColor: "#1c2630"
                    strokeColor: borderSoft
                    implicitHeight: supportCol.implicitHeight + 34

                    Column {
                        id: supportCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10

                        Label { text: "Stack y soporte"; color: textPrimary; font.pixelSize: 20; font.family: "Segoe UI" }
                        AppTextArea { width: parent.width; readOnly: true; text: localStackTextValue; implicitHeight: 90 }
                        AppTextArea { width: parent.width; readOnly: true; text: repoBridgeTextValue; implicitHeight: 90 }
                        AppTextArea { width: parent.width; readOnly: true; text: developmentPacketValue; implicitHeight: 90 }

                        Label { text: "Progreso rapido"; color: textPrimary; font.pixelSize: 16; font.family: "Segoe UI" }
                        Repeater {
                            model: progressCardsModel
                            delegate: Label {
                                width: supportCol.width
                                text: modelData.title + ": " + modelData.value + " | " + (modelData.detail || "")
                                color: textSecondary
                                wrapMode: Label.WordWrap
                                font.pixelSize: 11
                                font.family: "Segoe UI"
                            }
                        }

                        // ToolHealthPanel integrado (Task B)
                        ToolHealthPanel {
                            id: toolHealthPanel
                            width: parent.width
                            providers: providerCardsModel
                            onRotateToolRequested: {
                                if (controlCenterViewModel) controlCenterViewModel.rotateToolRequested()
                            }
                            onHelpRequested: {
                                if (controlCenterViewModel) controlCenterViewModel.helpRequested()
                            }
                            onRefreshRequested: {
                                if (controlCenterViewModel) controlCenterViewModel.refreshProviderHealth()
                            }
                        }

                        // Conexion IA externa (MCP bridge - Capa 1)
                        Rectangle {
                            id: mcpBridgeCard
                            width: parent.width
                            radius: 8
                            color: "#111827"
                            border.color: controlCenterViewModel && controlCenterViewModel.mcpBridgeBlocked ? "#dc2626" : (controlCenterViewModel && controlCenterViewModel.mcpBridgeRunning ? "#16a34a" : "#334155")
                            border.width: 1
                            implicitHeight: mcpBridgeColumn.implicitHeight + 24

                            ColumnLayout {
                                id: mcpBridgeColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Label {
                                        text: "Conexion IA externa (MCP)"
                                        color: textPrimary
                                        font.pixelSize: 14
                                        font.bold: true
                                        font.family: "Segoe UI"
                                        Layout.fillWidth: true
                                    }

                                    Switch {
                                        id: mcpBridgeSwitch
                                        checked: Boolean(controlCenterViewModel && controlCenterViewModel.mcpBridgeEnabled)
                                        onToggled: {
                                            if (controlCenterViewModel) controlCenterViewModel.toggleMcpBridge(mcpBridgeSwitch.checked)
                                        }
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Label.WordWrap
                                    color: textSecondary
                                    font.pixelSize: 11
                                    font.family: "Segoe UI"
                                    text: {
                                        if (!controlCenterViewModel) return ""
                                        if (controlCenterViewModel.mcpBridgeBlocked) return "Bloqueado por governance: " + (controlCenterViewModel.mcpBridgeReason || "revisar autonomia")
                                        var st = controlCenterViewModel.mcpBridgeState || "stopped"
                                        if (st === "running") return "Activo. Agentes externos pueden consumir las 6 tools core."
                                        if (st === "starting") return "Iniciando servidor MCP y tunnel..."
                                        if (st === "failed") return "Fallo: " + (controlCenterViewModel.mcpBridgeReason || "ver logs")
                                        if (st === "stopping") return "Deteniendo..."
                                        return "Apagado. Activar para exponer el programa a Devin/Claude/Codex."
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    visible: Boolean(controlCenterViewModel && controlCenterViewModel.mcpTunnelUrl)
                                    spacing: 8

                                    TextField {
                                        id: mcpUrlField
                                        Layout.fillWidth: true
                                        readOnly: true
                                        text: controlCenterViewModel ? controlCenterViewModel.mcpTunnelUrl : ""
                                        color: textPrimary
                                        font.pixelSize: 11
                                        font.family: "Consolas"
                                    }

                                    Button {
                                        text: "Copiar URL"
                                        onClicked: {
                                            if (controlCenterViewModel) controlCenterViewModel.copyMcpTunnelUrl()
                                        }
                                    }
                                }
                            }
                        }

                        // BackgroundActivityChip integrado (Task B)
                        BackgroundActivityChip {
                            id: backgroundChip
                            anchors.horizontalCenter: parent.horizontalCenter
                            activityText: {
                                if (!controlCenterViewModel) return ""
                                var activity = controlCenterViewModel.backgroundActivity || {}
                                return activity.text || ""
                            }
                            progress: {
                                if (!controlCenterViewModel) return 0
                                var activity = controlCenterViewModel.backgroundActivity || {}
                                return activity.progress || 0
                            }
                            status: {
                                if (!controlCenterViewModel) return "idle"
                                var activity = controlCenterViewModel.backgroundActivity || {}
                                return activity.status || "idle"
                            }
                            visible: status !== "idle" && activityText !== ""
                        }
                    }
                }
            }
            }
        }
    }

    // Dialogos evolutivos (Task B) — ahora hosteados globalmente en Main.qml
}
