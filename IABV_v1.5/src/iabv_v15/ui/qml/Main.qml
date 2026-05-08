import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

ApplicationWindow {
    id: window
    readonly property color primaryBackground: "#111417"
    readonly property color textPrimary: "#f7fbfd"
    readonly property color textSecondary: "#d1d8df"
    readonly property color accentCyan: "#73d7d4"
    readonly property color accentAmber: "#c98a3d"
    readonly property color borderSoft: "#42505d"
    readonly property string titleFontFamily: "Segoe UI"
    readonly property string bodyFontFamily: "Segoe UI"

    property var navRoutes: navigationController ? navigationController.routes : [
        { key: "dashboard", title: "Resumen", subtitle: "Pulso local del sistema, modelos y memoria" },
        { key: "control", title: "Centro de Control", subtitle: "Roles de trabajo, paquete Codex y PBT" },
        { key: "capture", title: "Estudio de Ensenanza", subtitle: "Formulario de ensenanza, captura y revision multimodal" },
        { key: "evolution", title: "Centro Evolutivo", subtitle: "Autodiagnostico, dossiers y backlog priorizado" },
        { key: "knowledge", title: "Base de Conocimiento", subtitle: "Tareas confirmadas y memoria consultable" },
        { key: "providers", title: "Stack Local", subtitle: "Ollama, LM Studio, embeddings y salud tecnica" },
        { key: "runs", title: "Historial de Ejecuciones", subtitle: "Trazas por rol, severidad y dossiers" },
        { key: "centro_vivo", title: "Centro Vivo", subtitle: "Tablero operativo unificado: cola, IAs, heuristica, metricas y hallazgos" }
    ]
    property string activeRoute: navigationController ? navigationController.currentRoute : "dashboard"
    property string appTitleText: mainWindowBridge ? mainWindowBridge.appTitle : "IABV v1.5"
    property string statusText: mainWindowBridge ? mainWindowBridge.statusMessage : "Stack local por roles activo."
    property string workspaceRootText: mainWindowBridge ? mainWindowBridge.workspaceRoot : ""

    visible: true
    width: 1460
    height: 940
    minimumWidth: 1220
    minimumHeight: 780
    title: appTitleText
    color: primaryBackground

    Component.onCompleted: {
        // Hito honesto temprano: avisar a Python que la ApplicationWindow
        // root termino de evaluar su tree estatico (antes de los timers
        // de kickoff de los Loaders async).  Permite ver en el JSONL
        // si Component.onCompleted siquiera se ejecuta en Windows.
        if (mainWindowBridge) {
            mainWindowBridge.signal_main_qml_completed()
        }
        mainShellKickoff.start()
    }

    function routeSource(route) {
        if (route === "control") return Qt.resolvedUrl("pages/ControlCenterPage.qml")
        if (route === "capture") return Qt.resolvedUrl("pages/CaptureStudioPage.qml")
        if (route === "knowledge") return Qt.resolvedUrl("pages/KnowledgeBasePage.qml")
        if (route === "evolution") return Qt.resolvedUrl("pages/EvolutionCenterPage.qml")
        if (route === "providers") return Qt.resolvedUrl("pages/ProviderSettingsPage.qml")
        if (route === "runs") return Qt.resolvedUrl("pages/RunHistoryPage.qml")
        if (route === "centro_vivo") return Qt.resolvedUrl("pages/CentroVivoPage.qml")
        return Qt.resolvedUrl("pages/DashboardPage.qml")
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0f1418" }
            GradientStop { position: 0.55; color: "#151d24" }
            GradientStop { position: 1.0; color: "#1b232b" }
        }
    }

    // Fix 20c: Loading indicator — visible while mainShellLoader
    // is incubating the UI content.  Fades out once the shell is ready.
    Column {
        anchors.centerIn: parent
        spacing: 10
        visible: mainShellLoader.status !== Loader.Ready
        opacity: mainShellLoader.status !== Loader.Ready ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 400 } }

        BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            running: mainShellLoader.status !== Loader.Ready
            palette.dark: accentCyan
        }

        Label {
            text: "Cargando IABV..."
            color: textSecondary
            font.family: bodyFontFamily
            font.pixelSize: 16
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // Deferred setup indicator — visible while bootstrap runs
    // post-window background probes (tool pings, pip installs, etc.)
    Row {
        id: deferredSetupRow
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 8
        z: 10
        spacing: 6
        visible: mainWindowBridge ? mainWindowBridge.deferredSetupActive : false
        opacity: visible ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 300 } }

        BusyIndicator {
            implicitWidth: 16
            implicitHeight: 16
            running: deferredSetupRow.visible
            palette.dark: accentAmber
        }
        Label {
            text: "Finalizando inicializacion..."
            color: textSecondary
            font.family: bodyFontFamily
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Timer {
        id: mainShellKickoff
        interval: 25
        repeat: false
        running: false
        onTriggered: mainShellLoader.active = true
    }

    Loader {
        id: mainShellLoader
        objectName: "mainShellLoader"
        anchors.fill: parent
        active: false
        asynchronous: false
        sourceComponent: mainShellComponent
        // Sync loading: mainShellComponent is tiny (~160 lines: nav panel
        // + page Loader placeholder).  Loading synchronously takes < 10ms
        // and eliminates the dependency on the Qt render loop to drive the
        // QQmlIncubationController.  On Windows with QQmlApplicationEngine,
        // the render loop stops driving async incubation when the splash
        // occludes the main window — causing 60s+ starvation.
        //
        // We still report every transition so the JSONL shows exactly
        // when shell_loader_ready fires (now honest, not via fallback).
        onStatusChanged: {
            if (mainWindowBridge) {
                mainWindowBridge.signal_qml_loader_event("mainShellLoader", status, active)
            }
            if (status === Loader.Ready && mainWindowBridge) {
                mainWindowBridge.signal_shell_loader_ready()
            }
        }
        onActiveChanged: {
            if (mainWindowBridge) {
                mainWindowBridge.signal_qml_loader_event("mainShellLoader", status, active)
            }
        }
    }

    Component {
        id: mainShellComponent

        RowLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 16

            GlassPanel {
                Layout.fillHeight: true
                Layout.preferredWidth: 300
                radius: 28
                fillColor: "#18212a"
                strokeColor: borderSoft

                ScrollView {
                    id: navScroll
                    anchors.fill: parent
                    anchors.margins: 18
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Column {
                        width: navScroll.availableWidth
                        spacing: 16

                        Column {
                            width: parent.width
                            spacing: 4
                            Label {
                                text: "IABV"
                                color: textPrimary
                                font.family: titleFontFamily
                                font.pixelSize: 34
                                font.bold: true
                            }
                            Label {
                                text: "Nucleo de control local y entrenamiento"
                                color: textSecondary
                                font.family: bodyFontFamily
                                font.pixelSize: 14
                                wrapMode: Label.WordWrap
                            }
                        }

                        Repeater {
                            model: navRoutes
                            delegate: Rectangle {
                                width: navScroll.availableWidth
                                radius: 18
                                color: activeRoute === modelData.key ? "#263843" : "transparent"
                                border.width: 1
                                border.color: activeRoute === modelData.key ? accentCyan : borderSoft
                                implicitHeight: navText.implicitHeight + 28

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (navigationController) navigationController.navigate(modelData.key)
                                }

                                Column {
                                    id: navText
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 5
                                    Label {
                                        width: navText.width
                                        text: modelData.title
                                        color: textPrimary
                                        font.family: titleFontFamily
                                        font.pixelSize: 16
                                        wrapMode: Label.WordWrap
                                    }
                                    Label {
                                        width: navText.width
                                        text: modelData.subtitle
                                        color: textSecondary
                                        font.family: bodyFontFamily
                                        font.pixelSize: 12
                                        wrapMode: Label.WordWrap
                                    }
                                }
                            }
                        }

                        GlassPanel {
                            width: navScroll.availableWidth
                            radius: 20
                            fillColor: "#21303a"
                            strokeColor: borderSoft
                            implicitHeight: workspaceInfo.implicitHeight + 28

                            Column {
                                id: workspaceInfo
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                Label {
                                    text: "Espacio de trabajo"
                                    color: textSecondary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                }
                                Label {
                                    width: workspaceInfo.width
                                    text: workspaceRootText
                                    color: textPrimary
                                    font.family: bodyFontFamily
                                    font.pixelSize: 12
                                    wrapMode: Label.WordWrap
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                // Brecha 1.2: Track whether the initial (Dashboard) page has
                // loaded.  The first page is loaded synchronously for speed
                // (<10ms); subsequent page navigations use asynchronous
                // loading so they never freeze the UI thread.
                property bool initialPageLoaded: false

                Timer {
                    id: initialPageKickoff
                    interval: 50
                    repeat: false
                    running: false
                    onTriggered: pageLoader.active = true
                }

                // Secondary page preload stays disabled by default. These
                // pages execute ViewModel refresh logic when instantiated,
                // so invisible preloading can still block the event loop.
                // Real navigation remains on-demand through pageLoader.
                Timer {
                    id: secondaryPreloadKickoff
                    interval: 2000  // 2s after initial page ready
                    repeat: false
                    running: false
                    onTriggered: {
                        // Intentionally empty.
                    }
                }

                Loader {
                    id: pageLoader
                    objectName: "pageLoader"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: false
                    // Brecha 1.2: First page (Dashboard, 197 lines) loads
                    // synchronously for instant readiness.  After that,
                    // switch to async so heavy pages (EvolutionCenter 1395
                    // lines, CaptureStudio 2115 lines) don't freeze the UI.
                    asynchronous: parent.initialPageLoaded
                    source: routeSource(activeRoute)
                    onStatusChanged: {
                        if (mainWindowBridge) {
                            mainWindowBridge.signal_qml_loader_event("pageLoader", status, active)
                        }
                        if (status === Loader.Ready && mainWindowBridge) {
                            mainWindowBridge.signal_page_loader_ready()
                            if (!parent.initialPageLoaded) {
                                parent.initialPageLoaded = true
                                // Do not preload heavy pages after first paint.
                            }
                        }
                    }
                    onActiveChanged: {
                        if (mainWindowBridge) {
                            mainWindowBridge.signal_qml_loader_event("pageLoader", status, active)
                        }
                    }
                }

                // Brecha 1.2: Background preloaders for heavy secondary
                // pages.  These are invisible, zero-size Loaders that
                // compile the QML in background threads.  The compiled
                // component is cached by the QML engine, so when the user
                // navigates to one of these pages, pageLoader re-uses the
                // cached compilation and loads almost instantly.
                Loader {
                    id: controlPreloader
                    active: false
                    asynchronous: true
                    source: Qt.resolvedUrl("pages/ControlCenterPage.qml")
                    visible: false
                    width: 0; height: 0
                }
                Loader {
                    id: evolutionPreloader
                    active: false
                    asynchronous: true
                    source: Qt.resolvedUrl("pages/EvolutionCenterPage.qml")
                    visible: false
                    width: 0; height: 0
                }
                Loader {
                    id: capturePreloader
                    active: false
                    asynchronous: true
                    source: Qt.resolvedUrl("pages/CaptureStudioPage.qml")
                    visible: false
                    width: 0; height: 0
                }

                Component.onCompleted: initialPageKickoff.start()
            }
        }
    }

    // --- Global human-help dialogs (hosted at root so they work from any page) ---
    CredentialPromptDialog {
        id: globalCredentialDialog
        visible: false
        property var _sourceVm: null
        onCredentialProvided: function(payload) {
            if (_sourceVm) _sourceVm.onCredentialProvided(payload)
        }
        onDelegateToUser: function(payload) {
            if (_sourceVm) _sourceVm.onCredentialDelegated(payload)
        }
    }

    ClarificationDialog {
        id: globalClarificationDialog
        visible: false
        property var _sourceVm: null
        onClarificationResponse: function(payload) {
            if (_sourceVm) _sourceVm.onClarificationResponse(payload)
        }
    }

    MissingDependencyDialog {
        id: globalDependencyDialog
        visible: false
        property var _sourceVm: null
        onDependencyApproved: function(payload) {
            if (_sourceVm) _sourceVm.onDependencyApproved(payload)
        }
        onDependencyRejected: function(payload) {
            if (_sourceVm) _sourceVm.onDependencyRejected(payload)
        }
    }

    function _openCredentialDialog(vm, payload) {
        globalCredentialDialog._sourceVm = vm
        globalCredentialDialog.domain = payload.domain || ""
        globalCredentialDialog.reason = payload.reason || ""
        globalCredentialDialog.usernameHint = payload.username_hint || ""
        globalCredentialDialog.open()
    }
    function _openClarificationDialog(vm, payload) {
        globalClarificationDialog._sourceVm = vm
        globalClarificationDialog.requestId = payload.id || ""
        globalClarificationDialog.question = payload.question || ""
        globalClarificationDialog.options = payload.options || []
        globalClarificationDialog.context = payload.context || ""
        globalClarificationDialog.open()
    }
    function _openDependencyDialog(vm, payload) {
        globalDependencyDialog._sourceVm = vm
        globalDependencyDialog.packageName = payload.package_name || ""
        globalDependencyDialog.manager = payload.manager || ""
        globalDependencyDialog.reason = payload.reason || ""
        globalDependencyDialog.open()
    }

    Connections {
        target: controlCenterViewModel
        function onCredentialPromptRequested(payload) { _openCredentialDialog(controlCenterViewModel, payload) }
        function onClarificationRequested(payload) { _openClarificationDialog(controlCenterViewModel, payload) }
        function onMissingDependencyRequested(payload) { _openDependencyDialog(controlCenterViewModel, payload) }
    }
    Connections {
        target: evolutionCenterViewModel
        function onCredentialPromptRequested(payload) { _openCredentialDialog(evolutionCenterViewModel, payload) }
        function onClarificationRequested(payload) { _openClarificationDialog(evolutionCenterViewModel, payload) }
        function onMissingDependencyRequested(payload) { _openDependencyDialog(evolutionCenterViewModel, payload) }
    }
}

