import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"

Item {
    id: root
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color borderSoft: "#42505d"

    property var chatMessagesModel: controlCenterViewModel ? controlCenterViewModel.chatMessages : []
    property var providerCardsModel: controlCenterViewModel ? controlCenterViewModel.providerCards : []
    property var progressCardsModel: controlCenterViewModel ? controlCenterViewModel.progressCards : []
    property var evolutionOverviewModel: controlCenterViewModel ? controlCenterViewModel.evolutionOverview : ({})
    property var evolutionAreaCardsModel: controlCenterViewModel ? controlCenterViewModel.evolutionAreaCards : []
    property var evolutionBlockersModel: controlCenterViewModel ? controlCenterViewModel.evolutionBlockers : []
    property var liveProcessSummaryModel: controlCenterViewModel ? controlCenterViewModel.liveProcessSummary : ({})
    property var liveWorkItemsModel: controlCenterViewModel ? controlCenterViewModel.liveWorkItems : []
    property var assistantSessionCardsModel: controlCenterViewModel ? controlCenterViewModel.assistantSessionCards : []
    property var autonomyTimelineModel: controlCenterViewModel ? controlCenterViewModel.autonomyTimeline : []
    property var autonomyActivityModel: controlCenterViewModel ? controlCenterViewModel.autonomyActivity : ({})
    property var assistantActionButtonsModel: controlCenterViewModel ? controlCenterViewModel.assistantActionButtons : []
    property bool advancedVisible: controlCenterViewModel ? controlCenterViewModel.advancedVisible : false
    property bool workingState: controlCenterViewModel ? controlCenterViewModel.working : false
    property bool canApproveStrategyValue: controlCenterViewModel ? controlCenterViewModel.canApproveStrategy : false
    property bool canApproveNextPhaseValue: controlCenterViewModel ? controlCenterViewModel.canApproveNextPhase : false
    property bool canSimulateValue: controlCenterViewModel ? controlCenterViewModel.canSimulate : false
    property bool canExecuteValue: controlCenterViewModel ? controlCenterViewModel.canExecute : false
    property bool canAbortValue: controlCenterViewModel ? controlCenterViewModel.canAbort : false
    property bool canApproveObservationValue: controlCenterViewModel ? controlCenterViewModel.canApproveObservation : false
    property bool approvalDialogVisibleValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogVisible : false
    property bool liveDockExpanded: true
    property string routingModeLabelValue: controlCenterViewModel ? controlCenterViewModel.routingModeLabel : "Modo automatico"
    property string busyLabelText: controlCenterViewModel ? controlCenterViewModel.busyLabel : "Listo"
    property string clipboardNoticeValue: controlCenterViewModel ? controlCenterViewModel.clipboardNotice : ""
    property string assistantGuidanceModeValue: controlCenterViewModel ? controlCenterViewModel.assistantGuidanceMode : "idle"
    property string assistantGuidanceTextValue: controlCenterViewModel ? controlCenterViewModel.assistantGuidanceText : "Describe una tarea y te dire si me falta ensenanza, aprobacion, revision evolutiva o apoyo de Codex."
    property string approvalDialogTitleValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogTitle : "Aprobacion requerida"
    property string approvalDialogTextValue: controlCenterViewModel ? controlCenterViewModel.approvalDialogText : ""
    property string recommendationTextValue: controlCenterViewModel ? controlCenterViewModel.recommendationText : ""
    property string strategyTextValue: controlCenterViewModel ? controlCenterViewModel.strategyText : ""
    property string diagnosticTextValue: controlCenterViewModel ? controlCenterViewModel.diagnosticText : "Diagnostico pendiente."
    property string diagnosticTruthStateValue: controlCenterViewModel ? controlCenterViewModel.diagnosticTruthState : ""
    property string repoBridgeTextValue: controlCenterViewModel ? controlCenterViewModel.repoBridgeText : ""
    property string localStackTextValue: controlCenterViewModel ? controlCenterViewModel.localStackText : ""
    property string developmentPacketValue: controlCenterViewModel ? controlCenterViewModel.developmentPacket : ""
    property string adaptiveStatusTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveStatusText : "Sin sesion"
    property string adaptiveIntentTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveIntentText : ""
    property string adaptiveContextTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveContextText : ""
    property string adaptiveStrategyTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveStrategyText : ""
    property string adaptiveExecutionTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveExecutionText : ""
    property string adaptiveEvidenceTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveEvidenceText : ""
    property string adaptiveEvolutionTextValue: controlCenterViewModel ? controlCenterViewModel.adaptiveEvolutionText : ""

    // ── Propiedades avanzadas del chat ──
    property int attachedFileCountValue: controlCenterViewModel ? controlCenterViewModel.attachedFileCount : 0
    property string liveStatusValue: controlCenterViewModel ? controlCenterViewModel.liveStatus : "idle"
    property var contextualSuggestionsModel: controlCenterViewModel ? controlCenterViewModel.contextualSuggestions : []
    property var attachedFilesModel: controlCenterViewModel ? controlCenterViewModel.attachedFiles : []

    Timer {
        id: autonomyDockTimer
        interval: 1500
        repeat: true
        running: Boolean(controlCenterViewModel) && (
            workingState
            || Boolean(autonomyActivityModel.visible)
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
                visible: chatMessagesModel.length === 0 && !Boolean(autonomyActivityModel.visible)
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
                        spacing: 6
                        visible: mainWindowBridge ? mainWindowBridge.deferredSetupActive : false
                        BusyIndicator { running: parent.visible; implicitWidth: 16; implicitHeight: 16 }
                        Label { text: "Finalizando inicializacion de herramientas..."; color: "#8899aa"; font.pixelSize: 11; font.family: "Segoe UI" }
                    }
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
                    ScrollView {
                        width: chatCol.width
                        implicitHeight: 300
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Column {
                            width: parent.width
                            spacing: 10

                            Repeater {
                                model: chatMessagesModel
                                delegate: ChatMessageDelegate {
                                    width: chatCol.width
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
                            }
                        }
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
                    ChatToolbar {
                        id: chatToolbar
                        width: chatCol.width
                        toolCount: controlCenterViewModel ? controlCenterViewModel.providerCards.length : 0
                        activeProvider: routingModeLabelValue.toLowerCase().indexOf("chatgpt") >= 0 ? "chatgpt" : (routingModeLabelValue.toLowerCase().indexOf("claude") >= 0 ? "claude" : (routingModeLabelValue.toLowerCase().indexOf("devin") >= 0 ? "devin" : (routingModeLabelValue.toLowerCase().indexOf("ollama") >= 0 ? "ollama" : "auto")))
                        codeMode: false
                        canAttach: true
                        attachedCount: attachedFileCountValue
                        systemStatus: liveStatusValue === "idle" ? "idle" : (liveStatusValue === "error" ? "error" : "processing")
                        onAttachClicked: {
                            if (controlCenterViewModel) controlCenterViewModel.attachFile("test.txt", "C:/tmp/test.txt", 1024, "text/plain")
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

                    // ── Panel de sugerencias contextuales ──
                    ContextualSuggestionsPanel {
                        id: suggestionsPanel
                        width: chatCol.width
                        suggestions: contextualSuggestionsModel
                        onSuggestionClicked: function(action, text) {
                            if (controlCenterViewModel) controlCenterViewModel.handleSuggestionAction(action, text)
                        }
                        onDismissed: visible = false
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
                                        suggestionsPanel.visible = false;
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
                                AppButton { text: "Refrescar"; onClicked: if (controlCenterViewModel) controlCenterViewModel.refreshAutonomyDock() }
                            }

                            Label {
                                width: liveDockCol.width
                                text: liveProcessSummaryModel.summary || "Todavia no hay trabajo autonomo consolidado."
                                color: textSecondary
                                wrapMode: Label.WordWrap
                                font.pixelSize: 12
                                font.family: "Segoe UI"
                            }
                            RowLayout {
                                width: liveDockCol.width
                                spacing: 10

                                BusyIndicator {
                                    running: (liveProcessSummaryModel.status || "") === "awaiting_response" || (liveProcessSummaryModel.status || "") === "active"
                                    visible: running
                                    Layout.alignment: Qt.AlignTop
                                    implicitWidth: 22
                                    implicitHeight: 22
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    StatusPill {
                                        label: "Etapa: " + (liveProcessSummaryModel.stage || "sin actividad")
                                        accentColor: evolutionStatusColor(liveProcessSummaryModel.status || "idle")
                                        pulsing: (liveProcessSummaryModel.status || "") === "awaiting_response"
                                        minPillWidth: 170
                                        maxPillWidth: 340
                                    }
                                    StatusPill {
                                        label: "IA: " + (liveProcessSummaryModel.assistant_title || "motor local")
                                        accentColor: "#315c6e"
                                        minPillWidth: 150
                                        maxPillWidth: 260
                                    }
                                    StatusPill {
                                        label: "Lane: " + (liveProcessSummaryModel.lane || "local")
                                        accentColor: "#42505d"
                                        minPillWidth: 150
                                        maxPillWidth: 220
                                    }
                                    StatusPill {
                                        label: "Progreso: " + pctLabel(liveProcessSummaryModel.progress_pct) + "%"
                                        accentColor: "#3e7b63"
                                        minPillWidth: 150
                                        maxPillWidth: 220
                                    }
                                }
                            }

                            Rectangle {
                                width: liveDockCol.width
                                height: 10
                                radius: 5
                                color: "#24303a"
                                border.width: 1
                                border.color: borderSoft

                                Rectangle {
                                    width: Math.max(10, (parent.width - 2) * Math.max(0, Math.min(1, liveProcessSummaryModel.progress || 0)))
                                    height: parent.height - 2
                                    x: 1
                                    y: 1
                                    radius: 4
                                    color: evolutionStatusColor(liveProcessSummaryModel.status || "idle")
                                    visible: (liveProcessSummaryModel.progress || 0) > 0
                                }
                            }

                            Label { width: liveDockCol.width; text: "Objetivo: " + (liveProcessSummaryModel.goal_title || "sin objetivo") + (liveProcessSummaryModel.project_title ? " | Proyecto: " + liveProcessSummaryModel.project_title : ""); color: textPrimary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; text: "Paso actual: " + (liveProcessSummaryModel.current_step || "sin actividad") + " | Falta: " + pctLabel(liveProcessSummaryModel.remaining_pct) + "%"; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; visible: Boolean(liveProcessSummaryModel.pending_summary); text: "Pendiente: " + (liveProcessSummaryModel.pending_summary || ""); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; visible: Boolean(liveProcessSummaryModel.thread_title) || Boolean(liveProcessSummaryModel.thread_key); text: "Hilo activo: " + (liveProcessSummaryModel.thread_title || liveProcessSummaryModel.thread_key || "sin hilo"); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; visible: Boolean(liveProcessSummaryModel.blocker); text: "Bloqueo: " + (liveProcessSummaryModel.blocker || ""); color: "#ffd8b4"; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; visible: Boolean(liveProcessSummaryModel.human_help); text: "Ayuda humana: " + (liveProcessSummaryModel.human_help || ""); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                            Label { width: liveDockCol.width; text: "Ultimo experimento o evaluacion: " + (liveProcessSummaryModel.latest_experiment || "Sin evaluaciones recientes."); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }

                            Rectangle {
                                visible: Boolean(autonomyActivityModel.visible)
                                width: liveDockCol.width
                                radius: 14
                                color: "#17212a"
                                border.width: 1
                                border.color: evolutionStatusColor(autonomyActivityModel.status || "idle")
                                implicitHeight: liveActivityCol.implicitHeight + 16

                                Column {
                                    id: liveActivityCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6

                                    Label { text: autonomyActivityModel.title || "Actividad autonoma"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                                    Label { width: parent.width; text: autonomyActivityModel.detail || "Sin detalle."; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }
                                    Label { visible: Boolean(autonomyActivityModel.next_step); width: parent.width; text: "Siguiente paso: " + (autonomyActivityModel.next_step || ""); color: textPrimary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                                    Label { visible: Boolean(autonomyActivityModel.learning_note); width: parent.width; text: "Aprendizaje: " + (autonomyActivityModel.learning_note || ""); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                                    Label { visible: Boolean(autonomyActivityModel.human_help); width: parent.width; text: "Ayuda humana: " + (autonomyActivityModel.human_help || ""); color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 11; font.family: "Segoe UI" }
                                }
                            }

                            Rectangle {
                                visible: assistantGuidanceModeValue !== "idle" || assistantActionButtonsModel.length > 0
                                width: liveDockCol.width
                                radius: 14
                                color: "#17212a"
                                border.width: 1
                                border.color: assistantGuidanceModeValue === "need_approval" ? "#d9b15f" : (assistantGuidanceModeValue === "need_codex_fix" ? "#cf7e7e" : "#315c6e")
                                implicitHeight: liveGuidanceCol.implicitHeight + 16

                                Column {
                                    id: liveGuidanceCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6
                                    Label { text: "Siguiente gesto sugerido"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                                    Label { width: parent.width; text: assistantGuidanceTextValue; color: textSecondary; wrapMode: Label.WordWrap; font.pixelSize: 12; font.family: "Segoe UI" }
                                    Flow {
                                        width: parent.width
                                        spacing: 8
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

                            Column {
                                visible: liveDockExpanded
                                width: liveDockCol.width
                                spacing: 10

                                Label { text: "Sesiones de asistentes"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                                Repeater {
                                    model: assistantSessionCardsModel
                                    delegate: Rectangle {
                                        width: liveDockCol.width
                                        radius: 12
                                        color: "#1b252d"
                                        border.width: 1
                                        border.color: (modelData.coherence_flags && modelData.coherence_flags.length > 0) ? "#cf7e7e" : borderSoft
                                        implicitHeight: sessionCardCol.implicitHeight + 16

                                        Column {
                                            id: sessionCardCol
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 4
                                            Label { width: parent.width; text: modelData.title + " | " + (modelData.status || "n/d") + " | lane " + (modelData.lane || "n/d") + " | " + pctLabel(modelData.progress_pct) + "%"; color: textPrimary; font.pixelSize: 12; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { visible: Boolean(modelData.current_step); width: parent.width; text: "Paso actual: " + (modelData.current_step || ""); color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { visible: Boolean(modelData.thread_title) || Boolean(modelData.thread_key); width: parent.width; text: "Hilo: " + (modelData.thread_title || modelData.thread_key || "sin hilo"); color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { visible: Boolean(modelData.pending_summary); width: parent.width; text: "Pendiente: " + (modelData.pending_summary || ""); color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { visible: Boolean(modelData.blocker); width: parent.width; text: "Bloqueo: " + (modelData.blocker || ""); color: "#ffd8b4"; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { visible: modelData.coherence_flags && modelData.coherence_flags.length > 0; width: parent.width; text: "Coherencia: " + modelData.coherence_flags.join(" | "); color: "#ffd8b4"; font.pixelSize: 10; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                        }
                                    }
                                }

                                Label { text: "Trabajo vivo"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                                Repeater {
                                    model: liveWorkItemsModel
                                    delegate: Rectangle {
                                        width: liveDockCol.width
                                        radius: 12
                                        color: "#1b252d"
                                        border.width: 1
                                        border.color: evolutionStatusColor(modelData.status || "idle")
                                        implicitHeight: liveWorkCol.implicitHeight + 16

                                        Column {
                                            id: liveWorkCol
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 4
                                            Label { width: parent.width; text: modelData.assistant_title + " | " + modelData.stage + " | " + pctLabel(modelData.progress_pct) + "%"; color: textPrimary; font.pixelSize: 12; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Rectangle {
                                                width: parent.width
                                                height: 8
                                                radius: 4
                                                color: "#24303a"
                                                border.width: 1
                                                border.color: borderSoft
                                                Rectangle {
                                                    width: Math.max(8, (parent.width - 2) * Math.max(0, Math.min(1, (modelData.progress || 0))))
                                                    height: parent.height - 2
                                                    x: 1
                                                    y: 1
                                                    radius: 3
                                                    color: evolutionStatusColor(modelData.status || "idle")
                                                }
                                            }
                                            Label { width: parent.width; text: modelData.title; color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { width: parent.width; visible: Boolean(modelData.current_step); text: "Paso: " + (modelData.current_step || ""); color: textSecondary; font.pixelSize: 11; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { width: parent.width; visible: Boolean(modelData.pending_summary); text: "Pendiente: " + (modelData.pending_summary || ""); color: textSecondary; font.pixelSize: 10; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { width: parent.width; visible: Boolean(modelData.blocker); text: "Bloqueo: " + (modelData.blocker || ""); color: "#ffd8b4"; font.pixelSize: 10; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                            Label { width: parent.width; text: modelData.detail; color: textSecondary; font.pixelSize: 10; font.family: "Segoe UI"; wrapMode: Label.WordWrap }
                                        }
                                    }
                                }

                                Label { text: "Timeline"; color: textPrimary; font.pixelSize: 14; font.family: "Segoe UI" }
                                Repeater {
                                    model: autonomyTimelineModel
                                    delegate: Label {
                                        width: liveDockCol.width
                                        text: (modelData.assistant_title || "IABV") + ": " + modelData.title + " | " + (modelData.detail || "sin detalle")
                                        color: textSecondary
                                        font.pixelSize: 10
                                        font.family: "Segoe UI"
                                        wrapMode: Label.WordWrap
                                    }
                                }
                            }

                            Flow {
                                width: liveDockCol.width
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
                }
            }

            Column {
                width: parent.width
                spacing: 16
                visible: advancedVisible

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
                            providers: controlCenterViewModel ? controlCenterViewModel.providerCards : []
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

    // Dialogos evolutivos (Task B) — ahora hosteados globalmente en Main.qml
}
