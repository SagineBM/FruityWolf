import QtQuick
import QtQuick.Layouts
import ".."

// Premium Search Bar with keyboard shortcut hint
Rectangle {
    id: root
    
    property alias text: searchInput.text
    property string placeholder: "Search tracks, projects, tags..."
    property string shortcutHint: "Ctrl+F"
    
    signal search(string query)
    signal cleared()
    
    height: 48
    radius: Theme.radiusRound
    color: searchInput.activeFocus ? Theme.surfaceActive : Theme.surfaceHover
    border.width: searchInput.activeFocus ? 1 : 0
    border.color: Theme.borderAccent
    
    Behavior on color {
        ColorAnimation { duration: Theme.animFast }
    }
    
    Behavior on border.width {
        NumberAnimation { duration: Theme.animFast }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingMedium
        anchors.rightMargin: Theme.spacingMedium
        spacing: Theme.spacingSmall
        
        // Search icon
        SvgIcon {
            pathData: Icons.search
            size: 18
            color: searchInput.activeFocus ? Theme.accent : Theme.textMuted
            
            Behavior on color {
                ColorAnimation { duration: Theme.animFast }
            }
        }
        
        // Text input
        TextInput {
            id: searchInput
            Layout.fillWidth: true
            font.pixelSize: Theme.fontMedium
            color: Theme.text
            selectByMouse: true
            selectionColor: Theme.accent
            selectedTextColor: Theme.background
            
            // Placeholder
            Text {
                anchors.fill: parent
                text: root.placeholder
                font: parent.font
                color: Theme.textMuted
                visible: !parent.text && !parent.activeFocus
                verticalAlignment: Text.AlignVCenter
            }
            
            onTextChanged: {
                searchTimer.restart()
            }
            
            Keys.onEscapePressed: {
                text = ""
                root.cleared()
                focus = false
            }
            
            Timer {
                id: searchTimer
                interval: 250
                onTriggered: root.search(searchInput.text)
            }
        }
        
        // Keyboard shortcut hint
        Rectangle {
            visible: !searchInput.activeFocus && !searchInput.text
            width: shortcutText.implicitWidth + 12
            height: 22
            radius: Theme.radiusSmall
            color: Theme.glassBg
            border.width: 1
            border.color: Theme.glassBorder
            
            Text {
                id: shortcutText
                anchors.centerIn: parent
                text: root.shortcutHint
                font.pixelSize: Theme.fontXSmall
                font.family: "monospace"
                color: Theme.textMuted
            }
        }
        
        // Clear button
        IconButton {
            visible: searchInput.text
            iconPath: Icons.x
            iconSize: 16
            buttonSize: 32
            iconColor: Theme.textMuted
            
            onClicked: {
                searchInput.text = ""
                root.cleared()
            }
        }
    }
    
    // Focus on click
    MouseArea {
        anchors.fill: parent
        onClicked: searchInput.forceActiveFocus()
        z: -1
    }
    
    // Public function to focus
    function focus() {
        searchInput.forceActiveFocus()
    }
}
