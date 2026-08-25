import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/*
  Dialog modal para solicitar credenciales.
  Emite: credentialProvided({domain, username, password, remember})
         delegateToUser({domain, reason})
*/
Dialog {
    id: root
    modal: true
    focus: true
    closePolicy: Dialog.NoAutoClose
    
    property string domain: ""
    property string reason: ""
    property string usernameHint: ""
    property bool showDelegateOption: true
    
    signal credentialProvided(var payload)
    signal delegateToUser(var payload)
    
    title: "Credenciales requeridas"
    
    width: Math.min(420, parent.width * 0.9)
    anchors.centerIn: parent
    
    background: Rectangle {
        color: "#1b232b"
        border.color: "#42505d"
        border.width: 1
        radius: 14
    }
    
    header: Rectangle {
        color: "#18212a"
        height: 56
        radius: 14
        
        Label {
            anchors.fill: parent
            anchors.margins: 16
            text: root.title
            color: "#f7fbfd"
            font.family: "Segoe UI"
            font.pixelSize: 18
            font.bold: true
            verticalAlignment: Text.AlignVCenter
        }
    }
    
    contentItem: ColumnLayout {
        spacing: 16
        
        Label {
            text: "Dominio: " + root.domain
            color: "#d1d8df"
            font.family: "Segoe UI"
            font.pixelSize: 13
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        Label {
            text: "Motivo: " + root.reason
            color: "#d1d8df"
            font.family: "Segoe UI"
            font.pixelSize: 13
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
        
        TextField {
            id: usernameField
            placeholderText: root.usernameHint ? "Usuario (sugerido: " + root.usernameHint + ")" : "Usuario"
            text: root.usernameHint
            Layout.fillWidth: true
            color: "#f7fbfd"
            placeholderTextColor: "#6b7b8c"
            font.family: "Segoe UI"
            font.pixelSize: 14
            background: Rectangle {
                color: "#111417"
                border.color: usernameField.activeFocus ? "#73d7d4" : "#42505d"
                border.width: 1
                radius: 8
            }
        }
        
        TextField {
            id: passwordField
            placeholderText: "Contraseña"
            echoMode: TextInput.Password
            Layout.fillWidth: true
            color: "#f7fbfd"
            placeholderTextColor: "#6b7b8c"
            font.family: "Segoe UI"
            font.pixelSize: 14
            background: Rectangle {
                color: "#111417"
                border.color: passwordField.activeFocus ? "#73d7d4" : "#42505d"
                border.width: 1
                radius: 8
            }
        }
        
        CheckBox {
            id: rememberCheck
            text: "Recordar credenciales"
            checked: false
            contentItem: Text {
                text: rememberCheck.text
                color: "#d1d8df"
                font.family: "Segoe UI"
                font.pixelSize: 13
            }
        }
        
        Label {
            visible: root.showDelegateOption
            text: "O puedes delegar al usuario para que abra la ventana manualmente."
            color: "#8a9aaf"
            font.family: "Segoe UI"
            font.pixelSize: 12
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
    }
    
    footer: RowLayout {
        spacing: 12
        
        Button {
            text: "Delegar al usuario"
            visible: root.showDelegateOption
            Layout.fillWidth: true
            flat: true
            contentItem: Text {
                text: parent.text
                color: "#d1d8df"
                font.family: "Segoe UI"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: parent.hovered ? "#28333d" : "transparent"
                border.color: "#42505d"
                border.width: 1
                radius: 10
                implicitHeight: 44
            }
            onClicked: {
                root.delegateToUser({domain: root.domain, reason: root.reason})
                root.close()
            }
        }
        
        Button {
            text: "Cancelar"
            Layout.fillWidth: true
            flat: true
            contentItem: Text {
                text: parent.text
                color: "#d1d8df"
                font.family: "Segoe UI"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: parent.hovered ? "#28333d" : "transparent"
                border.color: "#42505d"
                border.width: 1
                radius: 10
                implicitHeight: 44
            }
            onClicked: root.close()
        }
        
        Button {
            text: "Aceptar"
            Layout.fillWidth: true
            enabled: usernameField.text.length > 0 && passwordField.text.length > 0
            contentItem: Text {
                text: parent.text
                color: enabled ? "#f7fbfd" : "#6b7b8c"
                font.family: "Segoe UI"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: enabled ? (parent.hovered ? "#2d6f79" : "#245e67") : "#1c252d"
                border.color: enabled ? "#7cd5d2" : "#42505d"
                border.width: 1
                radius: 10
                implicitHeight: 44
            }
            onClicked: {
                root.credentialProvided({
                    domain: root.domain,
                    username: usernameField.text,
                    password: passwordField.text,
                    remember: rememberCheck.checked
                })
                root.close()
            }
        }
    }
    
    onOpened: {
        usernameField.forceActiveFocus()
    }
}
