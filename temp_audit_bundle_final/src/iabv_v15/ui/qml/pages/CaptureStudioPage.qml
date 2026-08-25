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

    property var flowStepsModel: captureStudioViewModel ? captureStudioViewModel.flowSteps : []
    property var summaryCardsModel: captureStudioViewModel ? captureStudioViewModel.summaryCards : []
    property var policyCardsModel: captureStudioViewModel ? captureStudioViewModel.policyCards : []
    property var channelCardsModel: captureStudioViewModel ? captureStudioViewModel.channelCards : []
    property var reviewStepsModel: captureStudioViewModel ? captureStudioViewModel.reviewSteps : []
    property var teachingHistoryModel: captureStudioViewModel ? captureStudioViewModel.teachingHistory : []
    property var replayStepsModel: captureStudioViewModel ? captureStudioViewModel.replaySteps : []
    property var replayFramesModel: captureStudioViewModel ? captureStudioViewModel.replayFrames : []
    property var replayCurrentFrameModel: captureStudioViewModel ? captureStudioViewModel.replayCurrentFrame : ({})
    property var replayVisualSummaryModel: captureStudioViewModel ? captureStudioViewModel.replayVisualSummary : ({})
    property var assistantReplayCardsModel: captureStudioViewModel ? captureStudioViewModel.assistantReplayCards : []
    property var assistantReplayStepsModel: captureStudioViewModel ? captureStudioViewModel.assistantReplaySteps : []
    property var assistantLaneSummaryModel: captureStudioViewModel ? captureStudioViewModel.assistantLaneSummary : ({})
    property var replayAuditMetadata: replayVisualSummaryModel && replayVisualSummaryModel.metadata ? replayVisualSummaryModel.metadata : ({})
    property var selectedReplayStepModel: captureStudioViewModel ? captureStudioViewModel.selectedReplayStep : ({})
    property var selectedReplayAnnotationModel: captureStudioViewModel ? captureStudioViewModel.selectedReplayAnnotation : ({})
    property real replayZoomValue: captureStudioViewModel ? captureStudioViewModel.replayZoom : 1.0
    property string replayStatusFilterValue: captureStudioViewModel ? captureStudioViewModel.replayStatusFilter : "all"
    property bool replayCanGoPrevValue: captureStudioViewModel ? captureStudioViewModel.replayCanGoPrev : false
    property bool replayCanGoNextValue: captureStudioViewModel ? captureStudioViewModel.replayCanGoNext : false
    property bool annotationDrawModeValue: captureStudioViewModel ? captureStudioViewModel.annotationDrawMode : false
    property var selectedTeachingHistoryModel: captureStudioViewModel ? captureStudioViewModel.selectedTeachingHistory : ({})
    property var selectedPolicyModel: captureStudioViewModel ? captureStudioViewModel.selectedPolicy : ({})
    property var securityModel: captureStudioViewModel ? captureStudioViewModel.securityState : ({})
    property var sessionHealthModel: captureStudioViewModel ? captureStudioViewModel.sessionHealth : ({})
    property string loginStatusText: captureStudioViewModel ? captureStudioViewModel.loginStatus : ""
    property string teachingStatusText: captureStudioViewModel ? captureStudioViewModel.teachingStatus : ""
    property string teachingSummaryText: captureStudioViewModel ? captureStudioViewModel.teachingSummary : ""
    property int teachingDraftVersionValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftVersion : 0
    property string teachingDraftLessonTitleValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftLessonTitle : "Nueva ensenanza"
    property string teachingDraftTargetLabelValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftTargetLabel : ""
    property string teachingDraftStartUrlValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftStartUrl : ""
    property string teachingDraftObjectiveValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftObjective : ""
    property string teachingDraftExpectedOutcomeValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftExpectedOutcome : ""
    property string teachingDraftNotesValue: captureStudioViewModel ? captureStudioViewModel.teachingDraftNotes : ""
    property string activeEpisodeIdText: captureStudioViewModel ? captureStudioViewModel.activeEpisodeId : ""
    property bool sessionActiveState: captureStudioViewModel ? captureStudioViewModel.sessionActive : false
    property bool sessionPausedState: captureStudioViewModel ? captureStudioViewModel.sessionPaused : false
    property bool sessionFinalizingState: captureStudioViewModel ? captureStudioViewModel.sessionFinalizing : false
    property bool canStartState: captureStudioViewModel ? captureStudioViewModel.canStart : true
    property bool canPauseState: captureStudioViewModel ? captureStudioViewModel.canPause : false
    property bool canResumeState: captureStudioViewModel ? captureStudioViewModel.canResume : false
    property bool canStopState: captureStudioViewModel ? captureStudioViewModel.canStop : false
    property string captureProgressText: captureStudioViewModel ? captureStudioViewModel.captureProgressText : ""
    property string liveIncidentText: captureStudioViewModel ? captureStudioViewModel.liveIncidentText : "Sin incidencias"
    property int activeTab: 0
    property bool captureVisibleEnabled: true
    property bool captureBackgroundEnabled: true
    property bool captureApiEnabled: true

    function startTeachingCapture() {
        if (!captureStudioViewModel) {
            return
        }
        captureStudioViewModel.startTeaching(
            lessonTitleField.text,
            targetLabelField.text,
            startUrlField.text,
            objectiveField.text,
            outcomeField.text,
            notesField.text,
            captureVisibleEnabled,
            captureBackgroundEnabled,
            captureApiEnabled
        )
    }

    function syncTeachingDraftFields() {
        lessonTitleField.text = teachingDraftLessonTitleValue || "Nueva ensenanza"
        targetLabelField.text = teachingDraftTargetLabelValue || ""
        startUrlField.text = teachingDraftStartUrlValue || ""
        objectiveField.text = teachingDraftObjectiveValue || ""
        outcomeField.text = teachingDraftExpectedOutcomeValue || ""
        notesField.text = teachingDraftNotesValue || ""
        if (captureStudioViewModel) {
            captureStudioViewModel.previewTeachingTarget(startUrlField.text, targetLabelField.text)
        }
    }

    onTeachingDraftVersionValueChanged: syncTeachingDraftFields()
    Component.onCompleted: syncTeachingDraftFields()

    function replayStatusMatches(status) {
        if (replayStatusFilterValue === "all") {
            return true
        }
        if (replayStatusFilterValue === "green") {
            return status === "known" || status === "user_corrected"
        }
        if (replayStatusFilterValue === "orange") {
            return status === "uncertain"
        }
        if (replayStatusFilterValue === "red") {
            return status === "missing"
        }
        return true
    }

    function frameMatchesFilter(frameModel) {
        if (replayStatusFilterValue === "all") {
            return true
        }
        if (!frameModel || !frameModel.status_counts) {
            return false
        }
        if (replayStatusFilterValue === "green") {
            return (frameModel.status_counts.green || 0) > 0
        }
        if (replayStatusFilterValue === "orange") {
            return (frameModel.status_counts.orange || 0) > 0
        }
        if (replayStatusFilterValue === "red") {
            return (frameModel.status_counts.red || 0) > 0
        }
        return true
    }

    function replayAuditConfidenceLabel() {
        var value = replayAuditMetadata ? replayAuditMetadata.audit_overall_confidence : undefined
        if (value === undefined || value === null || value === "") {
            return "n/d"
        }
        return Number(value).toFixed(2)
    }

    function replayAuditPrimaryIssue() {
        if (replayAuditMetadata && replayAuditMetadata.audit_findings && replayAuditMetadata.audit_findings.length > 0) {
            return replayAuditMetadata.audit_findings[0]
        }

    function replayAuditDetailLine() {
        var details = []
        if (replayAuditMetadata && replayAuditMetadata.audit_findings && replayAuditMetadata.audit_findings.length > 1) {
            details.push("discrepancias: " + replayAuditMetadata.audit_findings.slice(1, 3).join(" | "))
        } else if (replayVisualSummaryModel && replayVisualSummaryModel.gaps && replayVisualSummaryModel.gaps.length > 0) {
            details.push("discrepancias: " + replayVisualSummaryModel.gaps.slice(0, 2).join(" | "))
        }
        if (replayAuditMetadata && replayAuditMetadata.audit_rationale && replayAuditMetadata.audit_rationale !== replayAuditPrimaryIssue()) {
            details.push("contexto: " + replayAuditMetadata.audit_rationale)
        }
        return details.join(" | ")
    }
        if (replayAuditMetadata && replayAuditMetadata.audit_rationale) {
            return replayAuditMetadata.audit_rationale
        }
        return "Sin hallazgos de auditoria disponibles."
    }

    Timer {
        id: liveCapturePoller
        interval: 1200
        repeat: true
        running: sessionActiveState && !sessionPausedState && !sessionFinalizingState
        triggeredOnStart: false
        onTriggered: if (captureStudioViewModel) captureStudioViewModel.pollTeachingSession()
    }

    function openReplayViewer(episodeId) {
        var targetId = episodeId && episodeId.length > 0 ? episodeId : activeEpisodeIdText
        if (!captureStudioViewModel || !targetId || targetId.length === 0) {
            return
        }
        captureStudioViewModel.showReplayGuided(targetId)
        replayPopup.open()
    }

    ScrollView {
        id: captureScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        Column {
            width: captureScroll.availableWidth
            spacing: 16

            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: heroColumn.implicitHeight + 34

                Column {
                    id: heroColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10

                    Label {
                        text: "Estudio de ensenanza"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 24
                        font.bold: true
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: "Prepara que vas a ensenar, inicia la captura y deja lista la recoleccion de interfaz visible, segundo plano y API para aprendizaje local."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 13
                        wrapMode: Label.WordWrap
                    }

                    Flow {
                        width: heroColumn.width
                        spacing: 10
                        StatusPill {
                            label: sessionFinalizingState ? "Finalizando" : (sessionActiveState ? (sessionPausedState ? "Captura pausada" : "Captura activa") : "Listo para ensenar")
                            accentColor: sessionFinalizingState ? "#8b6f33" : (sessionActiveState ? (sessionPausedState ? "#8b6f33" : "#2e6770") : "#4c5b66")
                            labelColor: textPrimary
                            pulsing: sessionActiveState && !sessionPausedState && !sessionFinalizingState
                        }
                        StatusPill {
                            label: securityModel.capture_visible_ok ? "captura visible ok" : "captura visible pendiente"
                            accentColor: securityModel.capture_visible_ok ? "#2e6770" : "#6b4f3a"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: securityModel.bridge_active ? "bridge activo" : "bridge esperando"
                            accentColor: securityModel.bridge_active ? "#2e6770" : "#5b6670"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: "frames detectados: " + (securityModel.frames_detected || 0)
                            accentColor: "#4c5b66"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: "API en modo inteligente"
                            accentColor: "#6e5a2e"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: selectedPolicyModel.display_name || "Politica generica"
                            accentColor: "#6e5a2e"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: sessionHealthModel.health_label || "Sin incidencias"
                            accentColor: (sessionHealthModel.health_flags && sessionHealthModel.health_flags.length > 0) ? "#8b5a33" : "#355a43"
                            labelColor: textPrimary
                        }
                        StatusPill {
                            label: "sesion ligera por sitio"
                            accentColor: "#2e6770"
                            labelColor: textPrimary
                        }
                    }

                    Label {
                        text: teachingStatusText
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: teachingSummaryText
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: liveIncidentText
                        color: (sessionHealthModel.health_flags && sessionHealthModel.health_flags.length > 0) ? "#ffd8b4" : textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        visible: captureProgressText.length > 0
                        text: captureProgressText
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        visible: activeEpisodeIdText.length > 0
                        text: "Episodio activo o reciente: " + activeEpisodeIdText
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }

                    Flow {
                        width: heroColumn.width
                        spacing: 10

                        AppButton {
                            visible: !sessionActiveState && !sessionFinalizingState
                            text: "Iniciar captura"
                            accent: true
                            enabled: canStartState
                            onClicked: root.startTeachingCapture()
                        }

                        AppButton {
                            visible: canPauseState
                            text: "Pausar"
                            enabled: canPauseState
                            onClicked: if (captureStudioViewModel) captureStudioViewModel.pauseTeaching()
                        }

                        AppButton {
                            visible: canResumeState
                            text: "Reanudar"
                            accent: true
                            enabled: canResumeState
                            onClicked: if (captureStudioViewModel) captureStudioViewModel.resumeTeaching()
                        }

                        AppButton {
                            text: sessionFinalizingState ? "Recopilando..." : "Detener y recopilar"
                            enabled: canStopState
                            onClicked: if (captureStudioViewModel) captureStudioViewModel.stopTeaching()
                        }
                    }

                    Label {
                        text: "Aqui controlas la sesion activa. El replay guiado se abre desde el historial de ensenanzas."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 16

                GlassPanel {
                    width: captureScroll.availableWidth > 1180 ? captureScroll.availableWidth * 0.62 - 8 : captureScroll.availableWidth
                    fillColor: "#1f2a33"
                    strokeColor: borderSoft
                    implicitHeight: teachingFormColumn.implicitHeight + 36

                    Column {
                        id: teachingFormColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Que vas a ensenar"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 20
                        }

                        Label {
                            text: "La captura viva actual usa navegador administrado. Esta ficha tambien documenta otros programas o flujos para que la IA conserve contexto y metadatos."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 10
                            AppTextField {
                                id: lessonTitleField
                                Layout.fillWidth: true
                                text: "Nueva ensenanza"
                                placeholderText: "Nombre de la ensenanza"
                            }
                            AppTextField {
                                id: targetLabelField
                                Layout.fillWidth: true
                                placeholderText: "Programa, pagina o flujo"
                                onTextChanged: if (captureStudioViewModel) captureStudioViewModel.previewTeachingTarget(startUrlField.text, text)
                            }
                        }

                        AppTextField {
                            id: startUrlField
                            width: parent.width
                            placeholderText: "URL inicial o punto de arranque"
                            onTextChanged: if (captureStudioViewModel) captureStudioViewModel.previewTeachingTarget(text, targetLabelField.text)
                        }

                        AppTextArea {
                            id: objectiveField
                            width: parent.width
                            implicitHeight: 96
                            placeholderText: "Objetivo operativo: que le vas a ensenar exactamente"
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 10
                            AppTextArea {
                                id: outcomeField
                                Layout.fillWidth: true
                                implicitHeight: 92
                                placeholderText: "Resultado esperado"
                            }
                            AppTextArea {
                                id: notesField
                                Layout.fillWidth: true
                                implicitHeight: 92
                                placeholderText: "Notas, restricciones o contexto adicional"
                            }
                        }

                        Label {
                            text: "Canales de captura"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 16
                        }

                        Flow {
                            width: parent.width
                            spacing: 10
                            AppButton {
                                text: captureVisibleEnabled ? "Visible activo" : "Visible"
                                accent: captureVisibleEnabled
                                onClicked: captureVisibleEnabled = !captureVisibleEnabled
                            }
                            AppButton {
                                text: captureBackgroundEnabled ? "Segundo plano activo" : "Segundo plano"
                                accent: captureBackgroundEnabled
                                onClicked: captureBackgroundEnabled = !captureBackgroundEnabled
                            }
                            AppButton {
                                text: captureApiEnabled ? "API activa" : "API"
                                accent: captureApiEnabled
                                onClicked: captureApiEnabled = !captureApiEnabled
                            }
                        }

                        Label {
                            text: "La URL y el sitio se detectan automaticamente. La ensenanza usa una sesion administrada ligera y solo reusa storage state por sitio."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: loginStatusText
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 10
                            AppTextField {
                                id: userClueField
                                Layout.fillWidth: true
                                placeholderText: "Registrar pista: ejemplo, se congelo al abrir otra pestana"
                            }
                            AppButton {
                                text: "Registrar pista"
                                enabled: userClueField.text.length > 0
                                onClicked: {
                                    if (captureStudioViewModel) captureStudioViewModel.recordUserClue(userClueField.text)
                                    userClueField.text = ""
                                }
                            }
                        }
                    }
                }

                GlassPanel {
                    width: captureScroll.availableWidth > 1180 ? captureScroll.availableWidth * 0.38 - 8 : captureScroll.availableWidth
                    fillColor: "#1c2630"
                    strokeColor: borderSoft
                    implicitHeight: rightSummaryColumn.implicitHeight + 34

                    Column {
                        id: rightSummaryColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: selectedPolicyModel.display_name || "Seguridad y resumen"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 20
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: securityModel.detail || "La redaccion ocurre antes de guardar episodios y artefactos."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: securityModel.vault_mode || ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: securityModel.capture_hint || ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: securityModel.credential_check || ""
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        Label {
                            text: loginStatusText
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }


                        Repeater {
                            model: summaryCardsModel
                            delegate: Rectangle {
                                width: rightSummaryColumn.width
                                radius: 16
                                color: "#293742"
                                border.width: 1
                                border.color: borderSoft
                                implicitHeight: summaryCardContent.implicitHeight + 22

                                Column {
                                    id: summaryCardContent
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4
                                    Label {
                                        text: modelData.title + "  " + modelData.value
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 15
                                        wrapMode: Label.WordWrap
                                    }
                                    Label {
                                        text: modelData.hint
                                        color: textSecondary
                                        wrapMode: Label.WordWrap
                                        font.family: bodyFontFamily
                                        font.pixelSize: 12
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 16

                GlassPanel {
                    width: captureScroll.availableWidth > 1180 ? 360 : captureScroll.availableWidth
                    fillColor: "#1f2a33"
                    strokeColor: borderSoft
                    implicitHeight: policyColumn.implicitHeight + 36

                    Column {
                        id: policyColumn
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Label {
                            text: "Politicas de navegador"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 20
                        }

                        Repeater {
                            model: policyCardsModel
                            delegate: Rectangle {
                                width: policyColumn.width
                                radius: 16
                                color: selectedPolicyModel.site_id === modelData.site_id ? "#324551" : "#2a3640"
                                border.width: 1
                                border.color: selectedPolicyModel.site_id === modelData.site_id ? "#73d7d4" : borderSoft
                                implicitHeight: policyCardContent.implicitHeight + 24

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (captureStudioViewModel) captureStudioViewModel.selectSite(modelData.site_id)
                                }

                                Column {
                                    id: policyCardContent
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 4
                                    Label {
                                        text: modelData.display_name
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 15
                                        wrapMode: Label.WordWrap
                                    }
                                    Label {
                                        text: modelData.domains
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 12
                                        wrapMode: Label.WordWrap
                                    }
                                    Label {
                                        text: "Captura: " + modelData.capture_mode + "  |  Reglas sensibles: " + modelData.sensitive_rules
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 12
                                        wrapMode: Label.WordWrap
                                    }
                                }
                            }
                        }
                    }
                }

                Column {
                    width: captureScroll.availableWidth > 1180 ? captureScroll.availableWidth - 376 : captureScroll.availableWidth
                    spacing: 16
                    GlassPanel {
                        width: parent.width
                        fillColor: "#1c2630"
                        strokeColor: borderSoft
                        implicitHeight: sessionColumn.implicitHeight + 34

                        Column {
                            id: sessionColumn
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            Label {
                                text: "Sesion y selectores"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 20
                            }

                            RowLayout {
                                width: parent.width
                                spacing: 10
                                AppTextField {
                                    id: loginSelectorField
                                    Layout.fillWidth: true
                                    text: selectedPolicyModel.login_selector || ""
                                    placeholderText: "Selector de login"
                                }
                                AppTextField {
                                    id: logoutSelectorField
                                    Layout.fillWidth: true
                                    text: selectedPolicyModel.logout_selector || ""
                                    placeholderText: "Selector de logout"
                                }
                                AppButton {
                                    text: "Guardar"
                                    accent: true
                                    onClicked: if (captureStudioViewModel) captureStudioViewModel.savePolicyDraft(selectedPolicyModel.site_id || "generic_web", loginSelectorField.text, logoutSelectorField.text)
                                }
                            }

                            Label {
                                text: "La sesion se conserva con storage state por sitio cuando la pagina lo permite. Si el sitio vuelve a pedir login, puedes seguir ensenando y la app volvera a guardar el estado al detener."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                            }

                            Label {
                                text: "No hay perfiles visibles en esta pantalla. La sesion administrada se prepara sola para entrenar sin pasos extra ni configuraciones manuales."
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                                wrapMode: Label.WordWrap
                            }
                        }
                    }

                    GlassPanel {
                        width: parent.width
                        fillColor: "#1c2630"
                        strokeColor: borderSoft
                        implicitHeight: tabColumn.implicitHeight + 34

                        Column {
                            id: tabColumn
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 14

                            Flow {
                                width: tabColumn.width
                                spacing: 10
                                AppButton { text: "Visible"; accent: activeTab === 0; onClicked: activeTab = 0 }
                                AppButton { text: "Segundo plano"; accent: activeTab === 1; onClicked: activeTab = 1 }
                                AppButton { text: "API"; accent: activeTab === 2; onClicked: activeTab = 2 }
                            }

                            Column {
                                visible: activeTab === 0
                                width: tabColumn.width
                                spacing: 10
                                Rectangle {
                                    width: parent.width
                                    radius: 16
                                    color: "#293742"
                                    border.width: 1
                                    border.color: borderSoft
                                    implicitHeight: visibleSummary.implicitHeight + 22
                                    Column {
                                        id: visibleSummary
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4
                                        Label {
                                            text: channelCardsModel.length > 0 ? channelCardsModel[0].title + "  " + channelCardsModel[0].count : "Visible"
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 16
                                        }
                                        Label {
                                            text: channelCardsModel.length > 0 ? channelCardsModel[0].detail : ""
                                            color: textSecondary
                                            wrapMode: Label.WordWrap
                                            font.family: bodyFontFamily
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                                Label {
                                    text: "La capa visible conserva timeline humano, pantallas y contexto de lo que el usuario realmente vio y realizo."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                            }

                            Column {
                                visible: activeTab === 1
                                width: tabColumn.width
                                spacing: 10
                                Rectangle {
                                    width: parent.width
                                    radius: 16
                                    color: "#293742"
                                    border.width: 1
                                    border.color: borderSoft
                                    implicitHeight: backgroundSummary.implicitHeight + 22
                                    Column {
                                        id: backgroundSummary
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4
                                        Label {
                                            text: channelCardsModel.length > 1 ? channelCardsModel[1].title + "  " + channelCardsModel[1].count : "Segundo plano"
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 16
                                        }
                                        Label {
                                            text: channelCardsModel.length > 1 ? channelCardsModel[1].detail : ""
                                            color: textSecondary
                                            wrapMode: Label.WordWrap
                                            font.family: bodyFontFamily
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                                Label {
                                    text: "Cadencia de aprendizaje"
                                    color: textPrimary
                                    font.family: titleFontFamily
                                    font.pixelSize: 16
                                }
                                Repeater {
                                    model: flowStepsModel
                                    delegate: Rectangle {
                                        width: tabColumn.width
                                        radius: 14
                                        color: "#2a3640"
                                        border.width: 1
                                        border.color: borderSoft
                                        implicitHeight: flowCardContent.implicitHeight + 18
                                        Column {
                                            id: flowCardContent
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 3
                                            Label {
                                                text: modelData.title
                                                color: textPrimary
                                                font.family: titleFontFamily
                                                font.pixelSize: 13
                                            }
                                            Label {
                                                text: modelData.hint
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                        }
                                    }
                                }
                            }

                            Column {
                                visible: activeTab === 2
                                width: tabColumn.width
                                spacing: 10
                                Rectangle {
                                    width: parent.width
                                    radius: 16
                                    color: "#293742"
                                    border.width: 1
                                    border.color: borderSoft
                                    implicitHeight: apiSummary.implicitHeight + 22
                                    Column {
                                        id: apiSummary
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 4
                                        Label {
                                            text: channelCardsModel.length > 2 ? channelCardsModel[2].title + "  " + channelCardsModel[2].count : "API"
                                            color: textPrimary
                                            font.family: titleFontFamily
                                            font.pixelSize: 16
                                        }
                                        Label {
                                            text: channelCardsModel.length > 2 ? channelCardsModel[2].detail : ""
                                            color: textSecondary
                                            wrapMode: Label.WordWrap
                                            font.family: bodyFontFamily
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                                Label {
                                    text: securityModel.local_first || ""
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                                Label {
                                    text: "Headers como authorization, cookie y set-cookie, ademas de passwords, emails y tokens en cuerpos JSON, se guardan enmascarados."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                            }
                        }
                    }
                }
            }


            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: assistantReplayColumn.implicitHeight + 34

                Column {
                    id: assistantReplayColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Replay de asistentes externos"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                    }

                    Label {
                        text: "Aqui revisas si Codex, ChatGPT, Claude u Ollama estan usando el hilo correcto, la lane correcta y si el aprendizaje realmente quedo capturado."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Flow {
                        width: parent.width
                        spacing: 10
                        StatusPill { label: "total: " + (assistantLaneSummaryModel.total || 0); accentColor: "#4c5b66"; labelColor: textPrimary }
                        StatusPill { label: "background: " + (assistantLaneSummaryModel.background || 0); accentColor: "#2e6770"; labelColor: textPrimary }
                        StatusPill { label: "app: " + (assistantLaneSummaryModel.app || 0); accentColor: "#6e5a2e"; labelColor: textPrimary }
                        StatusPill { label: "manual: " + (assistantLaneSummaryModel.manual || 0); accentColor: "#8b5a33"; labelColor: textPrimary }
                        StatusPill { label: "capturadas: " + (assistantLaneSummaryModel.captured || 0); accentColor: "#355a43"; labelColor: textPrimary }
                        StatusPill { label: "pendientes: " + (assistantLaneSummaryModel.pending || 0); accentColor: "#8b6f33"; labelColor: textPrimary }
                        StatusPill { label: "bloqueadas: " + (assistantLaneSummaryModel.blocked || 0); accentColor: "#7a4040"; labelColor: textPrimary }
                    }

                    Flow {
                        width: parent.width
                        spacing: 16

                        GlassPanel {
                            width: parent.width > 1180 ? parent.width * 0.42 - 8 : parent.width
                            fillColor: "#202b35"
                            strokeColor: borderSoft
                            implicitHeight: assistantReplayList.implicitHeight + 28

                            Column {
                                id: assistantReplayList
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Label { text: "Consultas recientes"; color: textPrimary; font.family: titleFontFamily; font.pixelSize: 16 }
                                Label { visible: assistantReplayCardsModel.length === 0; text: "Aun no hay consultas externas para auditar."; color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 12; wrapMode: Label.WordWrap }
                                Repeater {
                                    model: assistantReplayCardsModel
                                    delegate: Rectangle {
                                        width: assistantReplayList.width
                                        radius: 14
                                        color: assistantLaneSummaryModel.selected_task_id === modelData.task_id ? "#324551" : "#2a3640"
                                        border.width: 1
                                        border.color: modelData.status === "green" ? "#56d98e" : (modelData.status === "orange" ? "#f0a65b" : "#ff7f7f")
                                        implicitHeight: assistantReplayCardCol.implicitHeight + 20
                                        Column {
                                            id: assistantReplayCardCol
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 4
                                            Label { text: modelData.assistant_title + " | " + modelData.status_label + " | lane " + (modelData.lane || "n/d"); color: textPrimary; font.family: titleFontFamily; font.pixelSize: 13; wrapMode: Label.WordWrap }
                                            Label { text: modelData.title; color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 11; wrapMode: Label.WordWrap }
                                            Label { visible: Boolean(modelData.thread_title) || Boolean(modelData.thread_key); text: "Hilo: " + (modelData.thread_title || modelData.thread_key || "sin hilo"); color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 11; wrapMode: Label.WordWrap }
                                            Label { text: modelData.summary; color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 11; wrapMode: Label.WordWrap }
                                            Label { visible: modelData.coherence_flags && modelData.coherence_flags.length > 0; text: "Coherencia: " + modelData.coherence_flags.join(" | "); color: "#ffd8b4"; font.family: bodyFontFamily; font.pixelSize: 10; wrapMode: Label.WordWrap }
                                            Flow {
                                                width: assistantReplayCardCol.width
                                                spacing: 8
                                                AppButton { text: "Ver replay"; accent: assistantLaneSummaryModel.selected_task_id === modelData.task_id; onClicked: if (captureStudioViewModel) captureStudioViewModel.selectAssistantReplayTask(modelData.task_id) }
                                                AppButton { text: "Vas bien"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(modelData.task_id, "vas bien") }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        GlassPanel {
                            width: parent.width > 1180 ? parent.width * 0.58 - 8 : parent.width
                            fillColor: "#202b35"
                            strokeColor: borderSoft
                            implicitHeight: assistantReplayStepsCol.implicitHeight + 28

                            Column {
                                id: assistantReplayStepsCol
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Label { text: "Timeline y auditoria del asistente"; color: textPrimary; font.family: titleFontFamily; font.pixelSize: 16 }
                                Label { visible: assistantReplayStepsModel.length === 0; text: "Selecciona una consulta externa para revisar el hilo, la lane, la captura y el aprendizaje."; color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 12; wrapMode: Label.WordWrap }
                                Repeater {
                                    model: assistantReplayStepsModel
                                    delegate: Rectangle {
                                        width: assistantReplayStepsCol.width
                                        radius: 12
                                        color: "#1a232b"
                                        border.width: 1
                                        border.color: modelData.display_color || borderSoft
                                        implicitHeight: assistantReplayStepContent.implicitHeight + 16
                                        Column {
                                            id: assistantReplayStepContent
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 4
                                            Label { text: modelData.title + " | " + modelData.status; color: textPrimary; font.family: titleFontFamily; font.pixelSize: 12; wrapMode: Label.WordWrap }
                                            Label { text: modelData.detail; color: textSecondary; font.family: bodyFontFamily; font.pixelSize: 11; wrapMode: Label.WordWrap }
                                        }
                                    }
                                }

                                Flow {
                                    width: assistantReplayStepsCol.width
                                    spacing: 8
                                    visible: Boolean(assistantLaneSummaryModel.selected_task_id)
                                    AppButton { text: "Corrige ruta"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(assistantLaneSummaryModel.selected_task_id || "", "corrige ruta") }
                                    AppButton { text: "No uses este chat"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(assistantLaneSummaryModel.selected_task_id || "", "no uses este chat") }
                                    AppButton { text: "Aprendizaje util"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(assistantLaneSummaryModel.selected_task_id || "", "aprendizaje util") }
                                    AppButton { text: "Aprendizaje incorrecto"; onClicked: if (captureStudioViewModel) captureStudioViewModel.recordAssistantReplayFeedback(assistantLaneSummaryModel.selected_task_id || "", "aprendizaje incorrecto") }
                                }
                            }
                        }
                    }
                }
            }

            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: historyColumn.implicitHeight + 34

                Column {
                    id: historyColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Historial de ensenanza y replay guiado"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                    }

                    Label {
                        text: "Selecciona una ensenanza para revisar si la IA capto bien los pasos, los objetos detectados y los canales usados."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Flow {
                        width: parent.width
                        spacing: 16

                        GlassPanel {
                            width: historyColumn.width > 1180 ? historyColumn.width * 0.38 - 8 : historyColumn.width
                            fillColor: "#202b35"
                            strokeColor: borderSoft
                            implicitHeight: historyList.implicitHeight + 28

                            Column {
                                id: historyList
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Label {
                                    text: "Sesiones recientes"
                                    color: textPrimary
                                    font.family: titleFontFamily
                                    font.pixelSize: 16
                                }

                                Label {
                                    visible: teachingHistoryModel.length === 0
                                    text: "Aun no hay ensenanzas recuperables guardadas."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }

                                Repeater {
                                    model: teachingHistoryModel
                                    delegate: Rectangle {
                                        width: historyList.width
                                        radius: 14
                                        color: selectedTeachingHistoryModel.episode_id === modelData.episode_id ? "#324551" : "#2a3640"
                                        border.width: 1
                                        border.color: selectedTeachingHistoryModel.episode_id === modelData.episode_id ? "#73d7d4" : borderSoft
                                        implicitHeight: historyCardContent.implicitHeight + 20

                                        Column {
                                            id: historyCardContent
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 4
                                            Label {
                                                text: modelData.title
                                                color: textPrimary
                                                font.family: titleFontFamily
                                                font.pixelSize: 13
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: "Objetivo: " + (modelData.objective || "sin objetivo")
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: "Estado: " + modelData.status + " | replay: " + (modelData.replay_quality || "n/d") + " | canales: " + modelData.channels + " | visibles: " + modelData.visible_step_count + " | capturas: " + modelData.screenshot_count + " | API: " + modelData.api_artifact_count + " | incidentes: " + (modelData.incident_count || 0) + " | artefactos: " + modelData.artifact_count
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: "Aprendizaje: " + (modelData.learning_readiness || "insufficient") + " | login: " + (modelData.login_learning_status || "insufficient") + " | relevantes: " + (modelData.relevant_step_count || 0)
                                                color: (modelData.learning_readiness || "") === "ready" ? "#7df0a8" : textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Flow {
                                                width: historyCardContent.width
                                                spacing: 8
                                                AppButton {
                                                    text: "Ver replay guiado"
                                                    accent: selectedTeachingHistoryModel.episode_id === modelData.episode_id
                                                    implicitWidth: 170
                                                    enabled: modelData.has_recoverable_replay
                                                    onClicked: root.openReplayViewer(modelData.episode_id)
                                                }
                                                AppButton {
                                                    text: "Eliminar"
                                                    implicitWidth: 120
                                                    onClicked: if (captureStudioViewModel) captureStudioViewModel.deleteTeachingEpisode(modelData.episode_id)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        GlassPanel {
                            width: historyColumn.width > 1180 ? historyColumn.width * 0.62 - 8 : historyColumn.width
                            fillColor: "#202b35"
                            strokeColor: borderSoft
                            implicitHeight: replayColumn.implicitHeight + 28

                            Column {
                                id: replayColumn
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Label {
                                    text: selectedTeachingHistoryModel.title || "Replay guiado"
                                    color: textPrimary
                                    font.family: titleFontFamily
                                    font.pixelSize: 16
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    text: selectedTeachingHistoryModel.objective ? ("Objetivo: " + selectedTeachingHistoryModel.objective) : "Selecciona una ensenanza para ver el replay."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                                Label {
                                    visible: !!selectedTeachingHistoryModel.episode_id
                                    text: "Sitio: " + (selectedTeachingHistoryModel.site_id || "sin sitio") + " | estado: " + (selectedTeachingHistoryModel.status || "sin estado") + " | redacciones: " + (selectedTeachingHistoryModel.redacted_steps || 0) + " pasos, " + (selectedTeachingHistoryModel.redacted_network_fields || 0) + " campos de red"
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    visible: !!selectedTeachingHistoryModel.episode_id
                                    text: replayStepsModel.length > 0 ? ("Replay cargado con " + replayStepsModel.length + " pasos detectados.") : "Esta ensenanza aun no tiene pasos listos para replay."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    visible: !!selectedTeachingHistoryModel.episode_id
                                    text: "Aprendizaje: " + (selectedTeachingHistoryModel.learning_readiness || "insufficient") + " | login: " + (selectedTeachingHistoryModel.login_learning_status || "insufficient")
                                    color: (selectedTeachingHistoryModel.learning_readiness || "") === "ready" ? "#7df0a8" : textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    visible: !!selectedTeachingHistoryModel.episode_id && (selectedTeachingHistoryModel.learning_summary_text || selectedTeachingHistoryModel.login_learning_summary)
                                    text: (selectedTeachingHistoryModel.learning_summary_text || "") + ((selectedTeachingHistoryModel.learning_summary_text || "") && (selectedTeachingHistoryModel.login_learning_summary || "") ? " | " : "") + (selectedTeachingHistoryModel.login_learning_summary || "")
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    // Resumen textual minimo de la auditoria 2 planos del replay actual.
                                    visible: !!selectedTeachingHistoryModel.episode_id
                                    text: "Auditoria 2 planos | audit_status: " + (replayAuditMetadata.audit_status || "sin auditoria")
                                          + " | confianza: " + root.replayAuditConfidenceLabel()
                                          + " | hallazgo: " + root.replayAuditPrimaryIssue()
                                    color: (replayAuditMetadata.audit_status || "") === "confirmed" ? "#7df0a8"
                                           : ((replayAuditMetadata.audit_status || "") === "insufficient" ? "#ffb4a8" : "#ffd27f")
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    // Discrepancias o contexto extra de la misma auditoria ya mostrada arriba.
                                    visible: !!selectedTeachingHistoryModel.episode_id && root.replayAuditDetailLine().length > 0
                                    text: root.replayAuditDetailLine()
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 10
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    visible: !!selectedTeachingHistoryModel.episode_id && selectedTeachingHistoryModel.suggested_commands && selectedTeachingHistoryModel.suggested_commands.length > 0
                                    text: "Comando sugerido: " + selectedTeachingHistoryModel.suggested_commands[Math.min(1, selectedTeachingHistoryModel.suggested_commands.length - 1)]
                                    color: "#73d7d4"
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }

                                Label {
                                    visible: replayStepsModel.length === 0
                                    text: "El replay guiado aparecera aqui con accion, tipo de objeto, canal y detalle detectado."
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }

                                Repeater {
                                    model: replayStepsModel
                                    delegate: Rectangle {
                                        width: replayColumn.width
                                        radius: 14
                                        color: modelData.learning_relevant ? "#21382c" : (modelData.sensitive ? "#30414d" : "#2a3640")
                                        border.width: 1
                                        border.color: modelData.learning_relevant ? "#56d98e" : (modelData.sensitive ? "#d7a65a" : borderSoft)
                                        implicitHeight: replayCardContent.implicitHeight + 20

                                        Column {
                                            id: replayCardContent
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 4
                                            Label {
                                                text: "Paso " + modelData.step_index + " | " + modelData.action_type + " | " + modelData.element_role
                                                color: textPrimary
                                                font.family: titleFontFamily
                                                font.pixelSize: 13
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: modelData.detail
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 12
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                visible: modelData.learning_relevant && !!modelData.learning_reason
                                                text: "Aprendizaje clave: " + modelData.learning_reason
                                                color: "#7df0a8"
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Rectangle {
                                                visible: modelData.has_screenshot
                                                width: parent.width
                                                implicitHeight: screenshotPreview.paintedHeight > 0 ? Math.min(screenshotPreview.paintedHeight + 12, 220) : 180
                                                radius: 12
                                                color: "#1b242c"
                                                border.width: 1
                                                border.color: modelData.learning_relevant ? "#56d98e" : borderSoft

                                                Image {
                                                    id: screenshotPreview
                                                    anchors.fill: parent
                                                    anchors.margins: 6
                                                    source: modelData.screenshot_url || ""
                                                    asynchronous: true
                                                    cache: false
                                                    fillMode: Image.PreserveAspectFit
                                                }

                                                Rectangle {
                                                    visible: modelData.has_screenshot && modelData.learning_relevant && modelData.overlay_rect && modelData.overlay_rect.valid
                                                    color: "transparent"
                                                    border.width: 2
                                                    border.color: "#56d98e"
                                                    radius: 8
                                                    x: 6 + ((parent.width - 12 - screenshotPreview.paintedWidth) / 2) + (screenshotPreview.paintedWidth * modelData.overlay_rect.x)
                                                    y: 6 + ((parent.height - 12 - screenshotPreview.paintedHeight) / 2) + (screenshotPreview.paintedHeight * modelData.overlay_rect.y)
                                                    width: Math.max(18, screenshotPreview.paintedWidth * modelData.overlay_rect.width)
                                                    height: Math.max(18, screenshotPreview.paintedHeight * modelData.overlay_rect.height)
                                                }
                                            }
                                            Label {
                                                visible: !modelData.has_screenshot
                                                text: modelData.channel === "api" ? "Sin captura visible: este paso proviene de API inteligente recuperada." : "Sin captura visible en este paso. La accion puede venir de metadatos o segundo plano."
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: "Canal: " + modelData.channel + " | selector: " + modelData.selector + (modelData.frame_url ? (" | frame: " + modelData.frame_url) : "") + (modelData.screenshot_name ? (" | captura: " + modelData.screenshot_name) : "")
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassPanel {
                width: parent.width
                fillColor: "#1c2630"
                strokeColor: borderSoft
                implicitHeight: reviewColumn.implicitHeight + 34

                Column {
                    id: reviewColumn
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Label {
                        text: "Revision post sesion"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                    }

                    Label {
                        visible: reviewStepsModel.length === 0
                        text: "Cuando existan pasos capturados apareceran aqui ya redactados para revisar, confirmar y memorizar."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Repeater {
                        model: reviewStepsModel
                        delegate: Rectangle {
                            width: reviewColumn.width
                            radius: 16
                            color: modelData.sensitive ? "#30414d" : "#2a3640"
                            border.width: 1
                            border.color: modelData.sensitive ? "#d7a65a" : borderSoft
                            implicitHeight: reviewCardContent.implicitHeight + 22

                            Column {
                                id: reviewCardContent
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 4
                                Label {
                                    text: modelData.action_type + "  |  " + modelData.target
                                    color: textPrimary
                                    font.family: titleFontFamily
                                    font.pixelSize: 14
                                    wrapMode: Label.WordWrap
                                }
                                Label {
                                    text: modelData.text
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                                Label {
                                    text: modelData.timestamp
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 11
                                    wrapMode: Label.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: replayPopup
        parent: Overlay.overlay
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: Overlay.overlay
        width: parent ? Math.min(parent.width - 20, 1460) : Math.min(root.width - 20, 1460)
        height: parent ? Math.min(parent.height - 20, 940) : Math.min(root.height - 20, 940)
        padding: 0
        property real replayViewportPadding: 32
        property real replayFitScale: {
            if (replayImage.status !== Image.Ready || replayImage.sourceSize.width <= 0 || replayImage.sourceSize.height <= 0 || galleryFlick.width <= 0 || galleryFlick.height <= 0) {
                return 1.0
            }
            var availableWidth = Math.max(260, galleryFlick.width - replayViewportPadding)
            var availableHeight = Math.max(180, galleryFlick.height - replayViewportPadding)
            return Math.min(availableWidth / replayImage.sourceSize.width, availableHeight / replayImage.sourceSize.height, 1.0)
        }
        property real replayEffectiveScale: replayFitScale * Math.max(0.5, replayZoomValue)

        function toggleReplayZoom() {
            if (!captureStudioViewModel) {
                return
            }
            captureStudioViewModel.setReplayZoom(replayZoomValue < 1.45 ? 2.0 : 1.0)
        }

        onOpened: {
            if (captureStudioViewModel) {
                captureStudioViewModel.setReplayZoom(1.0)
            }
            if (galleryFlick) {
                galleryFlick.contentX = 0
                galleryFlick.contentY = 0
            }
        }

        background: Rectangle {
            radius: 20
            color: "#172028"
            border.width: 1
            border.color: borderSoft
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: selectedTeachingHistoryModel.title || "Replay guiado ampliado"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 20
                        font.bold: true
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: selectedTeachingHistoryModel.objective ? ("Objetivo: " + selectedTeachingHistoryModel.objective) : "Selecciona una ensenanza para revisar el replay paso a paso."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 12
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: "Replay cargado con " + replayStepsModel.length + " pasos detectados."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: "Login aprendido: " + (selectedTeachingHistoryModel.login_learning_status || "insufficient") + " | Aprendizaje: " + (selectedTeachingHistoryModel.learning_readiness || "insufficient") + " | Verde/Naranja/Rojo: " + (replayVisualSummaryModel.green_count || 0) + "/" + (replayVisualSummaryModel.orange_count || 0) + "/" + (replayVisualSummaryModel.red_count || 0)
                        color: "#7df0a8"
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        visible: selectedTeachingHistoryModel.suggested_commands && selectedTeachingHistoryModel.suggested_commands.length > 0
                        text: "Comando sugerido: " + selectedTeachingHistoryModel.suggested_commands[Math.min(1, selectedTeachingHistoryModel.suggested_commands.length - 1)]
                        color: "#73d7d4"
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }

                    Label {
                        text: "Doble clic sobre la imagen para ampliar o volver al ajuste."
                        color: textSecondary
                        font.family: bodyFontFamily
                        font.pixelSize: 11
                        wrapMode: Label.WordWrap
                    }
                }

                AppButton {
                    text: "Cerrar replay"
                    implicitWidth: 160
                    onClicked: replayPopup.close()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: 14
                color: "#1d2831"
                border.width: 1
                border.color: borderSoft
                implicitHeight: 78

                Flow {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    StatusPill {
                        label: "Galeria visual"
                        accentColor: "#2e6770"
                        labelColor: textPrimary
                    }
                    StatusPill {
                        label: "Timeline de eventos"
                        accentColor: "#4b5d69"
                        labelColor: textPrimary
                    }
                    StatusPill {
                        label: "Filmstrip"
                        accentColor: "#5f6b38"
                        labelColor: textPrimary
                    }
                    StatusPill {
                        label: "frames utiles: " + (replayVisualSummaryModel.useful_frames || 0)
                        accentColor: "#355a43"
                        labelColor: textPrimary
                    }
                    StatusPill {
                        label: "correcciones: " + (replayVisualSummaryModel.manual_correction_count || 0)
                        accentColor: "#8b6f33"
                        labelColor: textPrimary
                    }
                    StatusPill {
                        label: annotationDrawModeValue ? "Modo dibujo activo" : "Modo dibujo inactivo"
                        accentColor: annotationDrawModeValue ? "#8b5a33" : "#42505d"
                        labelColor: textPrimary
                    }
                    AppButton { text: "Todo"; accent: replayStatusFilterValue === "all"; onClicked: if (captureStudioViewModel) captureStudioViewModel.setReplayStatusFilter("all") }
                    AppButton { text: "Verde"; accent: replayStatusFilterValue === "green"; onClicked: if (captureStudioViewModel) captureStudioViewModel.setReplayStatusFilter("green") }
                    AppButton { text: "Naranja"; accent: replayStatusFilterValue === "orange"; onClicked: if (captureStudioViewModel) captureStudioViewModel.setReplayStatusFilter("orange") }
                    AppButton { text: "Rojo"; accent: replayStatusFilterValue === "red"; onClicked: if (captureStudioViewModel) captureStudioViewModel.setReplayStatusFilter("red") }
                }
            }

            ScrollView {
                id: replayBodyScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                Column {
                    width: replayBodyScroll.availableWidth
                    spacing: 12

                    RowLayout {
                        width: parent.width
                        height: Math.max(340, replayPopup.height * 0.42)
                        spacing: 14

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: Math.max(620, replayPopup.width * 0.62)
                    radius: 18
                    color: "#1b242c"
                    border.width: 1
                    border.color: borderSoft

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            AppButton {
                                text: "Anterior"
                                enabled: replayCanGoPrevValue
                                onClicked: if (captureStudioViewModel) captureStudioViewModel.previousReplayFrame()
                            }
                            AppButton {
                                text: "Siguiente"
                                enabled: replayCanGoNextValue
                                onClicked: if (captureStudioViewModel) captureStudioViewModel.nextReplayFrame()
                            }
                            AppButton {
                                text: annotationDrawModeValue ? "Cancelar dibujo" : "Redibujar"
                                accent: annotationDrawModeValue
                                onClicked: if (captureStudioViewModel) captureStudioViewModel.beginAnnotationDraw()
                            }
                            Label {
                                text: "frame " + (replayFramesModel.length > 0 ? (replayCurrentFrameModel.frame_index + 1) : 0) + " / " + replayFramesModel.length
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: "Zoom"
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 12
                            }
                            Slider {
                                id: zoomSlider
                                from: 0.5
                                to: 3.0
                                stepSize: 0.05
                                value: replayZoomValue
                                Layout.preferredWidth: 180
                                onMoved: if (captureStudioViewModel) captureStudioViewModel.setReplayZoom(value)
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: Math.max(220, replayPopup.height * 0.27)
                            Layout.preferredHeight: Math.max(260, replayPopup.height * 0.33)
                            radius: 14
                            color: "#121920"
                            border.width: 1
                            border.color: borderSoft

                            Flickable {
                                id: galleryFlick
                                anchors.fill: parent
                                anchors.margins: 10
                                clip: true
                                interactive: !annotationDrawModeValue
                                boundsBehavior: Flickable.StopAtBounds
                                flickableDirection: Flickable.AutoFlickDirection
                                contentWidth: replayCanvasSurface.width
                                contentHeight: replayCanvasSurface.height

                                Item {
                                    id: replayCanvasSurface
                                    width: Math.max(galleryFlick.width, replayImage.status === Image.Ready ? replayImage.sourceSize.width * replayPopup.replayEffectiveScale : galleryFlick.width - 24)
                                    height: Math.max(galleryFlick.height, replayImage.status === Image.Ready ? replayImage.sourceSize.height * replayPopup.replayEffectiveScale : galleryFlick.height - 24)

                                    Image {
                                        id: replayImage
                                        anchors.centerIn: parent
                                        source: replayCurrentFrameModel.screenshot_url || ""
                                        cache: false
                                        asynchronous: true
                                        smooth: true
                                        width: replayImage.status === Image.Ready ? replayImage.sourceSize.width * replayPopup.replayEffectiveScale : Math.max(420, galleryFlick.width - 32)
                                        height: replayImage.status === Image.Ready ? replayImage.sourceSize.height * replayPopup.replayEffectiveScale : Math.max(320, galleryFlick.height - 32)
                                        fillMode: Image.PreserveAspectFit
                                    }

                                    TapHandler {
                                        enabled: !annotationDrawModeValue
                                        acceptedButtons: Qt.LeftButton
                                        onDoubleTapped: replayPopup.toggleReplayZoom()
                                    }

                                    Label {
                                        anchors.centerIn: parent
                                        visible: replayImage.status !== Image.Ready
                                        width: Math.min(parent.width - 40, 460)
                                        text: replayCurrentFrameModel.screenshot_url ? "Cargando captura principal..." : "Esta captura no tiene imagen principal disponible."
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 14
                                        horizontalAlignment: Label.AlignHCenter
                                        wrapMode: Label.WordWrap
                                    }

                                    Item {
                                        id: overlayCanvas
                                        visible: replayImage.status === Image.Ready
                                        x: replayImage.x
                                        y: replayImage.y
                                        width: replayImage.width
                                        height: replayImage.height

                                        Repeater {
                                            model: replayCurrentFrameModel.overlays || []
                                            delegate: Item {
                                                anchors.fill: parent
                                                property bool isActive: (selectedReplayAnnotationModel.annotation_id || "") === (modelData.annotation_id || "") || (selectedReplayStepModel.step_id || "") === (modelData.step_id || "")
                                                property bool matchesFilter: root.replayStatusMatches(modelData.annotation_status || "uncertain")

                                                Rectangle {
                                                    visible: matchesFilter && (modelData.overlay_kind === "rect" || modelData.overlay_kind === "text_span" || modelData.overlay_kind === "path") && modelData.overlay_rect && modelData.overlay_rect.valid
                                                    x: overlayCanvas.width * modelData.overlay_rect.x
                                                    y: overlayCanvas.height * modelData.overlay_rect.y
                                                    width: Math.max(18, overlayCanvas.width * modelData.overlay_rect.width)
                                                    height: Math.max(18, overlayCanvas.height * modelData.overlay_rect.height)
                                                    color: "transparent"
                                                    radius: 8
                                                    border.width: isActive ? 3 : 2
                                                    border.color: modelData.display_color || "#f0a65b"
                                                }

                                                Rectangle {
                                                    visible: matchesFilter && modelData.overlay_kind === "scroll_band"
                                                    x: modelData.overlay_rect && modelData.overlay_rect.valid ? overlayCanvas.width * modelData.overlay_rect.x : overlayCanvas.width * 0.92
                                                    y: modelData.overlay_rect && modelData.overlay_rect.valid ? overlayCanvas.height * modelData.overlay_rect.y : overlayCanvas.height * 0.06
                                                    width: modelData.overlay_rect && modelData.overlay_rect.valid ? Math.max(10, overlayCanvas.width * modelData.overlay_rect.width) : 12
                                                    height: modelData.overlay_rect && modelData.overlay_rect.valid ? Math.max(40, overlayCanvas.height * modelData.overlay_rect.height) : overlayCanvas.height * 0.82
                                                    radius: 8
                                                    color: Qt.rgba(0, 0, 0, 0.0)
                                                    border.width: isActive ? 3 : 2
                                                    border.color: modelData.display_color || "#f0a65b"
                                                }

                                                Rectangle {
                                                    visible: matchesFilter && modelData.overlay_kind === "click_point"
                                                    width: isActive ? 24 : 18
                                                    height: width
                                                    radius: width / 2
                                                    x: overlayCanvas.width * ((modelData.overlay_point && modelData.overlay_point.valid) ? modelData.overlay_point.x : ((modelData.overlay_rect && modelData.overlay_rect.valid) ? (modelData.overlay_rect.x + modelData.overlay_rect.width / 2) : 0.5)) - width / 2
                                                    y: overlayCanvas.height * ((modelData.overlay_point && modelData.overlay_point.valid) ? modelData.overlay_point.y : ((modelData.overlay_rect && modelData.overlay_rect.valid) ? (modelData.overlay_rect.y + modelData.overlay_rect.height / 2) : 0.5)) - height / 2
                                                    color: modelData.display_color || "#56d98e"
                                                    border.width: 2
                                                    border.color: "#ffffff"
                                                }

                                                Rectangle {
                                                    visible: matchesFilter && modelData.overlay_kind !== "click_point" && (!modelData.overlay_rect || !modelData.overlay_rect.valid) && modelData.overlay_point && modelData.overlay_point.valid
                                                    width: isActive ? 24 : 18
                                                    height: width
                                                    radius: 6
                                                    x: overlayCanvas.width * modelData.overlay_point.x - width / 2
                                                    y: overlayCanvas.height * modelData.overlay_point.y - height / 2
                                                    color: Qt.rgba(0.07, 0.09, 0.12, 0.68)
                                                    border.width: isActive ? 3 : 2
                                                    border.color: modelData.display_color || "#f0a65b"

                                                    Label {
                                                        anchors.centerIn: parent
                                                        text: (modelData.status_family || "orange") === "red" ? "!" : "?"
                                                        color: textPrimary
                                                        font.family: titleFontFamily
                                                        font.pixelSize: 12
                                                    }
                                                }

                                                Rectangle {
                                                    visible: matchesFilter && !!modelData.overlay_label
                                                    x: modelData.overlay_rect && modelData.overlay_rect.valid ? overlayCanvas.width * modelData.overlay_rect.x : Math.max(0, overlayCanvas.width * ((modelData.overlay_point && modelData.overlay_point.valid) ? modelData.overlay_point.x : 0.5) - 70)
                                                    y: modelData.overlay_rect && modelData.overlay_rect.valid ? Math.max(0, overlayCanvas.height * modelData.overlay_rect.y - 24) : Math.max(0, overlayCanvas.height * ((modelData.overlay_point && modelData.overlay_point.valid) ? modelData.overlay_point.y : 0.5) - 26)
                                                    width: Math.min(220, overlayLabel.implicitWidth + 18)
                                                    height: overlayLabel.implicitHeight + 8
                                                    radius: 8
                                                    color: Qt.rgba(0.07, 0.09, 0.12, 0.88)
                                                    border.width: 1
                                                    border.color: modelData.display_color || "#f0a65b"

                                                    Label {
                                                        id: overlayLabel
                                                        anchors.centerIn: parent
                                                        text: modelData.overlay_label || "objeto"
                                                        color: textPrimary
                                                        font.family: bodyFontFamily
                                                        font.pixelSize: 11
                                                        wrapMode: Label.WordWrap
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    enabled: !annotationDrawModeValue && matchesFilter
                                                    acceptedButtons: Qt.LeftButton
                                                    hoverEnabled: true
                                                    onClicked: if (captureStudioViewModel && modelData.annotation_id) captureStudioViewModel.selectReplayAnnotation(modelData.annotation_id)
                                                }
                                            }
                                        }

                                        Rectangle {
                                            id: draftAnnotationRect
                                            visible: annotationDrawMouse.dragging
                                            color: Qt.rgba(0.34, 0.85, 0.56, 0.12)
                                            border.width: 2
                                            border.color: "#56d98e"
                                            radius: 8
                                            x: Math.min(annotationDrawMouse.startX, annotationDrawMouse.currentX)
                                            y: Math.min(annotationDrawMouse.startY, annotationDrawMouse.currentY)
                                            width: Math.abs(annotationDrawMouse.currentX - annotationDrawMouse.startX)
                                            height: Math.abs(annotationDrawMouse.currentY - annotationDrawMouse.startY)
                                        }

                                        MouseArea {
                                            id: annotationDrawMouse
                                            anchors.fill: parent
                                            enabled: annotationDrawModeValue
                                            acceptedButtons: Qt.LeftButton
                                            preventStealing: true
                                            cursorShape: annotationDrawModeValue ? Qt.CrossCursor : Qt.ArrowCursor
                                            property bool dragging: false
                                            property real startX: 0
                                            property real startY: 0
                                            property real currentX: 0
                                            property real currentY: 0
                                            onPressed: {
                                                dragging = true
                                                startX = mouse.x
                                                startY = mouse.y
                                                currentX = mouse.x
                                                currentY = mouse.y
                                            }
                                            onPositionChanged: {
                                                if (!dragging) return
                                                currentX = Math.max(0, Math.min(mouse.x, overlayCanvas.width))
                                                currentY = Math.max(0, Math.min(mouse.y, overlayCanvas.height))
                                            }
                                            onReleased: {
                                                if (!dragging) return
                                                dragging = false
                                                var left = Math.max(0, Math.min(startX, currentX))
                                                var top = Math.max(0, Math.min(startY, currentY))
                                                var drawWidth = Math.abs(currentX - startX)
                                                var drawHeight = Math.abs(currentY - startY)
                                                if (drawWidth > 6 && drawHeight > 6 && captureStudioViewModel) {
                                                    captureStudioViewModel.commitAnnotationRect(left / overlayCanvas.width, top / overlayCanvas.height, drawWidth / overlayCanvas.width, drawHeight / overlayCanvas.height)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Label {
                                visible: annotationDrawModeValue
                                text: 'Modo dibujo activo: arrastra sobre la imagen para encerrar el objeto. Pulsa Cancelar dibujo cuando termines.'
                                color: '#ffd8b4'
                                font.family: bodyFontFamily
                                font.pixelSize: 11
                                wrapMode: Label.WordWrap
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent.width
                                spacing: 10

                                AppButton {
                                    text: "Marcar verde"
                                    enabled: !!selectedReplayAnnotationModel.annotation_id
                                    onClicked: if (captureStudioViewModel && selectedReplayAnnotationModel.annotation_id) captureStudioViewModel.setReplayAnnotationStatus(selectedReplayAnnotationModel.annotation_id, "known")
                                }
                                AppButton {
                                    text: "Marcar naranja"
                                    enabled: !!selectedReplayAnnotationModel.annotation_id
                                    onClicked: if (captureStudioViewModel && selectedReplayAnnotationModel.annotation_id) captureStudioViewModel.setReplayAnnotationStatus(selectedReplayAnnotationModel.annotation_id, "uncertain")
                                }
                                AppButton {
                                    text: "Marcar rojo"
                                    enabled: !!selectedReplayAnnotationModel.annotation_id
                                    onClicked: if (captureStudioViewModel && selectedReplayAnnotationModel.annotation_id) captureStudioViewModel.setReplayAnnotationStatus(selectedReplayAnnotationModel.annotation_id, "missing")
                                }
                                AppButton {
                                    text: "Guardar etiqueta"
                                    enabled: !!selectedReplayAnnotationModel.annotation_id
                                    onClicked: if (captureStudioViewModel && selectedReplayAnnotationModel.annotation_id) captureStudioViewModel.setReplayAnnotationLabel(selectedReplayAnnotationModel.annotation_id, annotationLabelField.text)
                                }
                                AppButton {
                                    text: "Eliminar anotacion"
                                    enabled: !!selectedReplayAnnotationModel.annotation_id
                                    onClicked: if (captureStudioViewModel && selectedReplayAnnotationModel.annotation_id) captureStudioViewModel.clearReplayAnnotation(selectedReplayAnnotationModel.annotation_id)
                                }
                            }

                            AppTextField {
                                id: annotationLabelField
                                Layout.fillWidth: true
                                text: selectedReplayAnnotationModel.overlay_label || selectedReplayStepModel.overlay_label || selectedReplayStepModel.text || ""
                                placeholderText: "Etiqueta del objeto o evento"
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: Math.min(320, replayPopup.width * 0.25)
                    Layout.minimumWidth: 280
                    Layout.fillHeight: true
                    radius: 18
                    color: "#1b242c"
                    border.width: 1
                    border.color: borderSoft

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        Label {
                            text: "Timeline de eventos"
                            color: textPrimary
                            font.family: titleFontFamily
                            font.pixelSize: 18
                        }

                        Label {
                            text: selectedReplayStepModel.detail || "Selecciona un evento para revisar el detalle y la anotacion activa."
                            color: textSecondary
                            font.family: bodyFontFamily
                            font.pixelSize: 12
                            wrapMode: Label.WordWrap
                        }

                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            Column {
                                width: parent.width
                                spacing: 8

                                Repeater {
                                    model: replayStepsModel
                                    delegate: Rectangle {
                                        width: parent.width
                                        visible: root.replayStatusMatches(modelData.annotation_status || "uncertain")
                                        radius: 12
                                        color: (modelData.annotation_status === "known" || modelData.annotation_status === "user_corrected") ? "#20382b" : (modelData.annotation_status === "missing" ? "#3b2626" : "#2a3640")
                                        border.width: (selectedReplayStepModel.step_id || "") === (modelData.step_id || "") ? 2 : 1
                                        border.color: modelData.display_color || borderSoft
                                        implicitHeight: timelineContent.implicitHeight + 18

                                        Column {
                                            id: timelineContent
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 4

                                            Label {
                                                text: "Paso " + modelData.step_index + " | " + modelData.action_type + " | " + modelData.element_role
                                                color: textPrimary
                                                font.family: titleFontFamily
                                                font.pixelSize: 12
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: modelData.detail
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 11
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                visible: !!modelData.learning_reason
                                                text: "Aprendizaje clave: " + modelData.learning_reason
                                                color: modelData.display_color || "#7df0a8"
                                                font.family: bodyFontFamily
                                                font.pixelSize: 10
                                                wrapMode: Label.WordWrap
                                            }
                                            Label {
                                                text: "confianza: " + Number(modelData.confidence_score || 0).toFixed(2) + " | canal: " + modelData.channel
                                                color: textSecondary
                                                font.family: bodyFontFamily
                                                font.pixelSize: 10
                                                wrapMode: Label.WordWrap
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: if (captureStudioViewModel) captureStudioViewModel.selectReplayStep(index)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

                    Rectangle {
                        width: parent.width
                        radius: 16
                        color: "#1c2630"
                        border.width: 1
                        border.color: borderSoft
                        implicitHeight: 104

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Label {
                        text: "Filmstrip"
                        color: textPrimary
                        font.family: titleFontFamily
                        font.pixelSize: 16
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        implicitHeight: 72
                        orientation: ListView.Horizontal
                        spacing: 10
                        model: replayFramesModel
                        clip: true

                        delegate: Rectangle {
                            width: 150
                            height: 78
                            opacity: root.frameMatchesFilter(modelData) ? 1.0 : 0.35
                            radius: 10
                            color: "#151d24"
                            border.width: replayCurrentFrameModel.frame_id === modelData.frame_id ? 2 : 1
                            border.color: (modelData.status_counts && modelData.status_counts.red > 0) ? "#ff6b6b" : ((modelData.status_counts && modelData.status_counts.orange > 0) ? "#f0a65b" : "#56d98e")

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 4

                                Image {
                                    width: parent.width
                                    height: 44
                                    source: modelData.screenshot_url || ""
                                    asynchronous: true
                                    cache: false
                                    fillMode: Image.PreserveAspectFit
                                }

                                Label {
                                    text: (index + 1) + ". overlays: " + (modelData.overlay_count || 0)
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 10
                                    wrapMode: Label.WordWrap
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: if (captureStudioViewModel) captureStudioViewModel.openReplayFrame(index)
                            }
                        }
                    }
                    }
                }
            }
        }
    }

}

}


