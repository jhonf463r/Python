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
        asynchronous: true
        sourceComponent: mainShellComponent
        // Hito honesto de readiness: solo cuando el contenido async del
        // shell termino de instanciarse, le avisamos a Python que el
        // splash puede empezar a desvanecer.  Antes el splash recibia
        // `ready` mientras esto seguia compilando en background.
        //
        // Ademas reportamos cada transicion (status y active) para que
        // el JSONL muestre exactamente que pasa con la incubacion del
        // Loader async en Windows pythonw.exe (donde a veces el
        // QQmlIncubator parece no llegar a Loader.Ready en >100s).
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

                Timer {
                    id: initialPageKickoff
                    interval: 50
                    repeat: false
                    running: false
                    onTriggered: pageLoader.active = true
                }

                Loader {
                    id: pageLoader
                    objectName: "pageLoader"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    active: false
                    asynchronous: true
                    source: routeSource(activeRoute)
                    // Cada transicion del page loader interno se reporta
                    // tambien.  Cuando alcanza Loader.Ready el usuario
                    // realmente ve la pagina (Dashboard u otra ruta) —
                    // hito ``page_loader_ready`` mas honesto que el del
                    // shell exterior.
                    onStatusChanged: {
                        if (mainWindowBridge) {
                            mainWindowBridge.signal_qml_loader_event("pageLoader", status, active)
                        }
                        if (status === Loader.Ready && mainWindowBridge) {
                            mainWindowBridge.signal_page_loader_ready()
                        }
                    }
                    onActiveChanged: {
                        if (mainWindowBridge) {
                            mainWindowBridge.signal_qml_loader_event("pageLoader", status, active)
                        }
                    }
                }

                Component.onCompleted: initialPageKickoff.start()
            }
        }
    }
}

