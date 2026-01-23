import QtQuick
import QtQuick.Layouts
import ".."

// Track List Item - Premium design with enhanced Now Playing state
Rectangle {
    id: root
    
    property var track
    property bool isPlaying: false
    property bool isSelected: false
    
    signal clicked()
    signal doubleClicked()
    signal favoriteClicked()
    signal playClicked()
    
    height: 64
    radius: Theme.radiusMedium
    
    // Distinct states: Playing > Selected > Hover > Default
    color: isPlaying 
           ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.15)
           : (isSelected ? Theme.surfaceActive : (mouseArea.containsMouse ? Theme.surfaceHover : "transparent"))
    
    border.width: isPlaying ? 1 : 0
    border.color: isPlaying ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.3) : "transparent"
    
    Behavior on color {
        ColorAnimation { duration: Theme.animFast }
    }
    
    Behavior on border.color {
        ColorAnimation { duration: Theme.animFast }
    }
    
    // Left accent border for Now Playing
    Rectangle {
        id: playingBorder
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: 3
        height: parent.height - 16
        radius: 1.5
        color: Theme.accent
        visible: root.isPlaying
        
        // Subtle pulse animation
        SequentialAnimation on opacity {
            running: root.isPlaying
            loops: Animation.Infinite
            NumberAnimation { to: 1; duration: 1000; easing.type: Easing.InOutQuad }
            NumberAnimation { to: 0.6; duration: 1000; easing.type: Easing.InOutQuad }
        }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingMedium
        anchors.rightMargin: Theme.spacingMedium
        spacing: Theme.spacingMedium
        
        // Play indicator / Number
        Rectangle {
            width: 40
            height: 40
            radius: Theme.radiusSmall
            color: isPlaying ? Theme.accentGlow : "transparent"
            
            // Playing animation bars
            Row {
                visible: root.isPlaying
                anchors.centerIn: parent
                spacing: 3
                
                Repeater {
                    model: 3
                    Rectangle {
                        width: 3
                        height: 12 + Math.random() * 8
                        radius: 1.5
                        color: Theme.accent
                        
                        SequentialAnimation on height {
                            running: root.isPlaying
                            loops: Animation.Infinite
                            NumberAnimation { to: 6 + Math.random() * 4; duration: 300 + Math.random() * 200 }
                            NumberAnimation { to: 16 + Math.random() * 6; duration: 300 + Math.random() * 200 }
                        }
                    }
                }
            }
            
            // Play button on hover (when not playing)
            SvgIcon {
                visible: mouseArea.containsMouse && !root.isPlaying
                anchors.centerIn: parent
                pathData: Icons.play
                size: 16
                color: Theme.text
                filled: true
            }
            
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.playClicked()
            }
        }
        
        // Track info
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            
            Text {
                text: track ? track.title : ""
                font.pixelSize: Theme.fontMedium
                font.weight: Font.Medium
                color: root.isPlaying ? Theme.accent : Theme.text
                Layout.fillWidth: true
                elide: Text.ElideRight
                
                Behavior on color {
                    ColorAnimation { duration: Theme.animFast }
                }
            }
            
            Text {
                text: track ? track.projectName : ""
                font.pixelSize: Theme.fontSmall
                color: Theme.textSecondary
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
        }
        
        // BPM badge
        Rectangle {
            visible: track && track.bpm
            width: 50
            height: 24
            radius: Theme.radiusSmall
            color: Theme.glassBg
            border.width: 1
            border.color: Theme.glassBorder
            
            Text {
                anchors.centerIn: parent
                text: track && track.bpm ? Math.round(track.bpm) : "--"
                font.pixelSize: Theme.fontSmall
                font.weight: Font.Medium
                color: Theme.textSecondary
            }
        }
        
        // Key badge
        Rectangle {
            visible: track && track.key
            width: 45
            height: 24
            radius: Theme.radiusSmall
            color: Theme.glassBg
            border.width: 1
            border.color: Theme.glassBorder
            
            Text {
                anchors.centerIn: parent
                text: track && track.key ? track.key : "--"
                font.pixelSize: Theme.fontSmall
                font.weight: Font.Medium
                color: Theme.secondary
            }
        }
        
        // Duration
        Text {
            text: track ? formatDuration(track.duration || 0) : "--:--"
            font.pixelSize: Theme.fontSmall
            color: Theme.textMuted
            Layout.preferredWidth: 45
            horizontalAlignment: Text.AlignRight
            
            function formatDuration(seconds) {
                var mins = Math.floor(seconds / 60)
                var secs = Math.floor(seconds % 60)
                return mins + ":" + (secs < 10 ? "0" : "") + secs
            }
        }
        
        // Favorite button
        IconButton {
            iconPath: track && track.favorite ? Icons.heartFilled : Icons.heart
            iconSize: 18
            buttonSize: 36
            iconColor: track && track.favorite ? "#f87171" : Theme.textMuted
            highlighted: track && track.favorite
            
            onClicked: root.favoriteClicked()
        }
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        propagateComposedEvents: true
        z: -1
        
        onClicked: root.clicked()
        onDoubleClicked: root.doubleClicked()
    }
}
