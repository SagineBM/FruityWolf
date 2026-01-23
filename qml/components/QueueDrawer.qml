import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

// Queue Drawer - Slides up from bottom to show upcoming tracks
Rectangle {
    id: root
    
    property var queueModel: []
    property var currentTrack: null
    property bool isPlaying: false
    
    signal playTrack(int trackId)
    signal removeFromQueue(int trackId)
    signal clearQueue()
    signal close()
    
    color: Theme.surface
    
    // Top border
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.border
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacingMedium
        spacing: Theme.spacingSmall
        
        // Header
        RowLayout {
            Layout.fillWidth: true
            
            Text {
                text: "Queue"
                font.pixelSize: Theme.fontLarge
                font.weight: Font.Bold
                color: Theme.text
            }
            
            Text {
                text: queueModel.length + " tracks"
                font.pixelSize: Theme.fontSmall
                color: Theme.textMuted
                Layout.leftMargin: Theme.spacingSmall
            }
            
            Item { Layout.fillWidth: true }
            
            // Clear queue button
            Rectangle {
                width: clearRow.implicitWidth + Theme.spacingMedium * 2
                height: 28
                radius: Theme.radiusSmall
                color: clearMouse.containsMouse ? Theme.surfaceHover : "transparent"
                visible: queueModel.length > 0
                
                Row {
                    id: clearRow
                    anchors.centerIn: parent
                    spacing: Theme.spacingXSmall
                    
                    SvgIcon {
                        pathData: Icons.trash
                        size: 14
                        color: Theme.textMuted
                    }
                    
                    Text {
                        text: "Clear"
                        font.pixelSize: Theme.fontSmall
                        color: Theme.textSecondary
                    }
                }
                
                MouseArea {
                    id: clearMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.clearQueue()
                }
            }
            
            // Close button
            IconButton {
                iconPath: Icons.x
                iconSize: 18
                buttonSize: 32
                tooltip: "Close queue (Q)"
                onClicked: root.close()
            }
        }
        
        // Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        
        // Now Playing section
        Rectangle {
            Layout.fillWidth: true
            height: 56
            radius: Theme.radiusMedium
            color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.1)
            border.width: 1
            border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2)
            visible: root.currentTrack !== null
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacingSmall
                spacing: Theme.spacingMedium
                
                // Playing indicator
                Rectangle {
                    width: 32
                    height: 32
                    radius: Theme.radiusSmall
                    color: Theme.accentGlow
                    
                    Row {
                        anchors.centerIn: parent
                        spacing: 2
                        
                        Repeater {
                            model: 3
                            Rectangle {
                                width: 3
                                height: 10 + Math.random() * 6
                                radius: 1.5
                                color: Theme.accent
                                
                                SequentialAnimation on height {
                                    running: root.isPlaying
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 6 + Math.random() * 4; duration: 300 + Math.random() * 200 }
                                    NumberAnimation { to: 14 + Math.random() * 4; duration: 300 + Math.random() * 200 }
                                }
                            }
                        }
                    }
                }
                
                Column {
                    Layout.fillWidth: true
                    spacing: 2
                    
                    Text {
                        text: "NOW PLAYING"
                        font.pixelSize: Theme.fontXSmall
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                        color: Theme.accent
                    }
                    
                    Text {
                        text: root.currentTrack ? root.currentTrack.title : ""
                        font.pixelSize: Theme.fontMedium
                        font.weight: Font.Medium
                        color: Theme.text
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
            }
        }
        
        // Up Next label
        Text {
            text: "UP NEXT"
            font.pixelSize: Theme.fontXSmall
            font.weight: Font.Bold
            font.letterSpacing: 1.5
            color: Theme.textMuted
            visible: queueModel.length > 0
            Layout.topMargin: Theme.spacingSmall
        }
        
        // Queue list
        ListView {
            id: queueList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: queueModel
            spacing: 2
            
            ScrollBar.vertical: ScrollBar {
                active: true
                policy: ScrollBar.AsNeeded
            }
            
            delegate: Rectangle {
                width: queueList.width - 8
                height: 48
                radius: Theme.radiusSmall
                color: delegateMouse.containsMouse ? Theme.surfaceHover : "transparent"
                
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spacingSmall
                    anchors.rightMargin: Theme.spacingSmall
                    spacing: Theme.spacingMedium
                    
                    // Position number
                    Text {
                        text: (index + 1).toString()
                        font.pixelSize: Theme.fontSmall
                        color: Theme.textMuted
                        Layout.preferredWidth: 24
                        horizontalAlignment: Text.AlignCenter
                    }
                    
                    // Track info
                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        
                        Text {
                            text: modelData.title || ""
                            font.pixelSize: Theme.fontMedium
                            color: Theme.text
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        
                        Text {
                            text: modelData.project_name || ""
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textSecondary
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                    
                    // Duration
                    Text {
                        text: formatDuration(modelData.duration || 0)
                        font.pixelSize: Theme.fontSmall
                        color: Theme.textMuted
                    }
                    
                    // Remove button (on hover)
                    IconButton {
                        visible: delegateMouse.containsMouse
                        iconPath: Icons.x
                        iconSize: 14
                        buttonSize: 28
                        tooltip: "Remove from queue"
                        onClicked: root.removeFromQueue(modelData.id)
                    }
                }
                
                MouseArea {
                    id: delegateMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    z: -1
                    onDoubleClicked: root.playTrack(modelData.id)
                }
            }
            
            // Empty state
            Column {
                anchors.centerIn: parent
                visible: queueModel.length === 0
                spacing: Theme.spacingSmall
                
                SvgIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    pathData: Icons.listMusic
                    size: 48
                    color: Theme.textMuted
                    opacity: 0.5
                }
                
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Queue is empty"
                    font.pixelSize: Theme.fontMedium
                    color: Theme.textSecondary
                }
                
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Play a track to start building your queue"
                    font.pixelSize: Theme.fontSmall
                    color: Theme.textMuted
                }
            }
        }
    }
    
    // Helper function
    function formatDuration(seconds) {
        var mins = Math.floor(seconds / 60)
        var secs = Math.floor(seconds % 60)
        return mins + ":" + (secs < 10 ? "0" : "") + secs
    }
}
