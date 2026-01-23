import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

// Keyboard Shortcuts Help Overlay - Press ? or F1 to show
Popup {
    id: root
    
    anchors.centerIn: parent
    width: 700
    height: 600
    modal: true
    dim: true
    padding: 0
    
    background: Rectangle {
        color: Theme.surfaceElevated
        radius: Theme.radiusXLarge
        border.width: 1
        border.color: Theme.border
        
        // Subtle gradient
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.05) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }
    
    contentItem: ColumnLayout {
        spacing: 0
        
        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingMedium
                
                SvgIcon {
                    pathData: Icons.keyboard
                    size: 28
                    color: Theme.accent
                }
                
                Text {
                    text: "Keyboard Shortcuts"
                    font.pixelSize: Theme.fontXLarge
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Item { Layout.fillWidth: true }
                
                // Close button
                IconButton {
                    iconPath: Icons.x
                    iconSize: 20
                    buttonSize: 36
                    onClicked: root.close()
                }
            }
        }
        
        // Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        
        // Shortcuts grid
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ColumnLayout {
                width: parent.width
                spacing: Theme.spacingLarge
                
                Item { Layout.preferredHeight: Theme.spacingMedium }
                
                // Playback section
                ShortcutSection {
                    title: "Playback"
                    shortcuts: [
                        { key: "Space", action: "Play / Pause" },
                        { key: "←", action: "Previous track" },
                        { key: "→", action: "Next track" },
                        { key: "↑", action: "Volume up" },
                        { key: "↓", action: "Volume down" },
                        { key: "M", action: "Toggle mute" },
                        { key: "S", action: "Toggle shuffle" },
                        { key: "R", action: "Cycle repeat mode" }
                    ]
                }
                
                // Navigation section
                ShortcutSection {
                    title: "Navigation"
                    shortcuts: [
                        { key: "Ctrl+F", action: "Focus search" },
                        { key: "Ctrl+1", action: "Go to Library" },
                        { key: "Ctrl+2", action: "Go to Favorites" },
                        { key: "Ctrl+3", action: "Go to Playlists" },
                        { key: "Ctrl+4", action: "Go to Settings" },
                        { key: "J", action: "Select next track" },
                        { key: "K", action: "Select previous track" },
                        { key: "Enter", action: "Play selected track" },
                        { key: "Esc", action: "Clear search" }
                    ]
                }
                
                // UI Controls section
                ShortcutSection {
                    title: "UI Controls"
                    shortcuts: [
                        { key: "B", action: "Toggle sidebar" },
                        { key: "D", action: "Toggle details panel" },
                        { key: "F5", action: "Rescan library" },
                        { key: "Ctrl+L", action: "Toggle favorite" },
                        { key: "?", action: "Show this help" }
                    ]
                }
                
                Item { Layout.preferredHeight: Theme.spacingMedium }
            }
        }
        
        // Footer
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 50
            color: Theme.glassBg
            
            Text {
                anchors.centerIn: parent
                text: "Press Escape or ? to close"
                font.pixelSize: Theme.fontSmall
                color: Theme.textMuted
            }
        }
    }
    
    // Shortcut section component
    component ShortcutSection: ColumnLayout {
        property string title: ""
        property var shortcuts: []
        
        Layout.fillWidth: true
        Layout.leftMargin: Theme.spacingLarge
        Layout.rightMargin: Theme.spacingLarge
        spacing: Theme.spacingSmall
        
        // Section title
        Text {
            text: title
            font.pixelSize: Theme.fontMedium
            font.weight: Font.Bold
            color: Theme.accent
            Layout.bottomMargin: Theme.spacingXSmall
        }
        
        // Shortcuts grid
        GridLayout {
            columns: 2
            columnSpacing: Theme.spacingXLarge
            rowSpacing: Theme.spacingSmall
            Layout.fillWidth: true
            
            Repeater {
                model: shortcuts
                
                RowLayout {
                    spacing: Theme.spacingMedium
                    Layout.preferredWidth: 280
                    
                    // Key badge
                    Rectangle {
                        Layout.preferredWidth: keyText.implicitWidth + 16
                        Layout.preferredHeight: 28
                        radius: Theme.radiusSmall
                        color: Theme.surface
                        border.width: 1
                        border.color: Theme.borderLight
                        
                        Text {
                            id: keyText
                            anchors.centerIn: parent
                            text: modelData.key
                            font.pixelSize: Theme.fontSmall
                            font.family: "Consolas, Monaco, monospace"
                            font.weight: Font.Medium
                            color: Theme.text
                        }
                    }
                    
                    // Action description
                    Text {
                        Layout.fillWidth: true
                        text: modelData.action
                        font.pixelSize: Theme.fontMedium
                        color: Theme.textSecondary
                    }
                }
            }
        }
    }
    
    // Animation
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.animMedium }
        NumberAnimation { property: "scale"; from: 0.95; to: 1; duration: Theme.animMedium; easing.type: Easing.OutBack }
    }
    
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.animFast }
        NumberAnimation { property: "scale"; from: 1; to: 0.95; duration: Theme.animFast }
    }
}
