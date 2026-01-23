import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import ".."

// Premium Player Bar with full controls
Rectangle {
    id: root
    
    property var currentTrack: null
    property bool isPlaying: false
    property real position: 0  // 0-1
    property real duration: 0  // seconds
    property real volume: 0.8  // 0-1
    property string repeatMode: "none"  // none, all, one
    property bool shuffleEnabled: false
    property bool sidebarVisible: true
    
    signal togglePlay()
    signal nextTrack()
    signal previousTrack()
    signal seek(real pos)
    signal setVolume(real vol)
    signal toggleMute()
    signal toggleShuffle()
    signal cycleRepeat()
    signal toggleSidebar()
    signal toggleFavorite()
    
    height: 90
    color: Theme.surface
    
    // Top border
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Theme.border
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingLarge
        anchors.rightMargin: Theme.spacingLarge
        spacing: Theme.spacingMedium
        
        // === LEFT: Track Info ===
        RowLayout {
            Layout.preferredWidth: 280
            spacing: Theme.spacingMedium
            
            // Album art / Waveform preview
            Rectangle {
                width: 56
                height: 56
                radius: Theme.radiusMedium
                visible: root.currentTrack !== null
                
                gradient: Gradient {
                    GradientStop { 
                        position: 0.0
                        color: root.currentTrack 
                            ? Qt.hsla((root.currentTrack.title.charCodeAt(0) % 360) / 360, 0.5, 0.25, 1) 
                            : Theme.surfaceHover 
                    }
                    GradientStop { 
                        position: 1.0
                        color: root.currentTrack 
                            ? Qt.hsla(((root.currentTrack.title.charCodeAt(0) + 40) % 360) / 360, 0.4, 0.15, 1) 
                            : Theme.surfaceHover 
                    }
                }
                
                Text {
                    anchors.centerIn: parent
                    text: root.currentTrack ? root.currentTrack.title.charAt(0).toUpperCase() : ""
                    font.pixelSize: 24
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                // Playing glow effect
                Rectangle {
                    visible: root.isPlaying
                    anchors.centerIn: parent
                    width: parent.width + 8
                    height: parent.height + 8
                    radius: parent.radius + 4
                    color: "transparent"
                    border.width: 2
                    border.color: Theme.accentGlow
                    opacity: 0.6
                    
                    SequentialAnimation on opacity {
                        running: root.isPlaying
                        loops: Animation.Infinite
                        NumberAnimation { to: 1; duration: 800 }
                        NumberAnimation { to: 0.3; duration: 800 }
                    }
                }
            }
            
            // Track text
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                
                Text {
                    text: root.currentTrack ? root.currentTrack.title : "No track selected"
                    font.pixelSize: Theme.fontMedium
                    font.weight: Font.Medium
                    color: Theme.text
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                
                Text {
                    text: root.currentTrack ? root.currentTrack.project_name : "Select a track to play"
                    font.pixelSize: Theme.fontSmall
                    color: Theme.textSecondary
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                
                // Metadata chips row (BPM • Key)
                Row {
                    spacing: Theme.spacingSmall
                    visible: root.currentTrack !== null
                    Layout.fillWidth: true
                    
                    // BPM chip
                    Rectangle {
                        visible: root.currentTrack && (root.currentTrack.bpm_user || root.currentTrack.bpm_detected || root.currentTrack.bpm)
                        width: bpmText.implicitWidth + 12
                        height: 20
                        radius: 4
                        color: Theme.glassBg
                        border.width: 1
                        border.color: Theme.glassBorder
                        
                        Text {
                            id: bpmText
                            anchors.centerIn: parent
                            text: {
                                var bpm = root.currentTrack ? (root.currentTrack.bpm_user || root.currentTrack.bpm_detected || root.currentTrack.bpm) : 0
                                return bpm ? Math.round(bpm) + " BPM" : ""
                            }
                            font.pixelSize: Theme.fontXSmall
                            font.weight: Font.Medium
                            color: Theme.accent
                        }
                    }
                    
                    // Key chip
                    Rectangle {
                        visible: root.currentTrack && (root.currentTrack.key_user || root.currentTrack.key_detected || root.currentTrack.key)
                        width: keyText.implicitWidth + 12
                        height: 20
                        radius: 4
                        color: Theme.glassBg
                        border.width: 1
                        border.color: Theme.glassBorder
                        
                        Text {
                            id: keyText
                            anchors.centerIn: parent
                            text: root.currentTrack ? (root.currentTrack.key_user || root.currentTrack.key_detected || root.currentTrack.key || "") : ""
                            font.pixelSize: Theme.fontXSmall
                            font.weight: Font.Medium
                            color: Theme.secondary
                        }
                    }
                }
            }
            
            // Favorite button
            IconButton {
                visible: root.currentTrack !== null
                iconPath: root.currentTrack && root.currentTrack.favorite ? Icons.heartFilled : Icons.heart
                iconSize: 18
                buttonSize: 36
                iconColor: root.currentTrack && root.currentTrack.favorite ? "#f87171" : Theme.textMuted
                tooltip: "Toggle favorite (Ctrl+L)"
                
                onClicked: root.toggleFavorite()
            }
        }
        
        Item { Layout.fillWidth: true }
        
        // === CENTER: Playback Controls ===
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spacingSmall
            
            // Control buttons row
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.spacingMedium
                
                // Shuffle
                IconButton {
                    iconPath: Icons.shuffle
                    iconSize: 18
                    buttonSize: 36
                    highlighted: root.shuffleEnabled
                    tooltip: "Shuffle (S)"
                    
                    onClicked: root.toggleShuffle()
                }
                
                // Previous
                IconButton {
                    iconPath: Icons.skipBack
                    iconSize: 22
                    buttonSize: 40
                    tooltip: "Previous (←)"
                    
                    onClicked: root.previousTrack()
                }
                
                // Play/Pause - Main button
                Rectangle {
                    width: 48
                    height: 48
                    radius: 24
                    color: playMouse.containsMouse ? Theme.accentHover : Theme.text
                    
                    scale: playMouse.pressed ? 0.95 : (playMouse.containsMouse ? 1.05 : 1)
                    Behavior on scale {
                        NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutBack }
                    }
                    
                    Behavior on color {
                        ColorAnimation { duration: Theme.animFast }
                    }
                    
                    SvgIcon {
                        anchors.centerIn: parent
                        anchors.horizontalCenterOffset: root.isPlaying ? 0 : 2
                        pathData: root.isPlaying ? Icons.pause : Icons.play
                        size: 20
                        color: Theme.background
                        filled: true
                    }
                    
                    MouseArea {
                        id: playMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.togglePlay()
                    }
                }
                
                // Next
                IconButton {
                    iconPath: Icons.skipForward
                    iconSize: 22
                    buttonSize: 40
                    tooltip: "Next (→)"
                    
                    onClicked: root.nextTrack()
                }
                
                // Repeat
                IconButton {
                    iconPath: root.repeatMode === "one" ? Icons.repeatOne : Icons.repeat
                    iconSize: 18
                    buttonSize: 36
                    highlighted: root.repeatMode !== "none"
                    tooltip: "Repeat: " + root.repeatMode + " (R)"
                    
                    onClicked: root.cycleRepeat()
                }
            }
            
            // Progress bar row
            RowLayout {
                Layout.preferredWidth: 500
                spacing: Theme.spacingSmall
                
                // Elapsed time
                Text {
                    text: formatTime(root.position * root.duration)
                    font.pixelSize: Theme.fontSmall
                    font.family: "monospace"
                    font.weight: Font.Medium
                    color: Theme.text
                    Layout.preferredWidth: 50
                }
                
                // Progress slider - enhanced for easier grabbing
                Slider {
                    id: progressSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    value: root.position
                    
                    background: Rectangle {
                        x: progressSlider.leftPadding
                        y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                        width: progressSlider.availableWidth
                        height: progressSlider.pressed || progressSlider.hovered ? 8 : 6
                        radius: height / 2
                        color: Theme.border
                        
                        Behavior on height {
                            NumberAnimation { duration: Theme.animFast }
                        }
                        
                        Rectangle {
                            width: progressSlider.visualPosition * parent.width
                            height: parent.height
                            radius: height / 2
                            
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Theme.accent }
                                GradientStop { position: 1.0; color: Theme.accentHover }
                            }
                        }
                    }
                    
                    handle: Rectangle {
                        x: progressSlider.leftPadding + progressSlider.visualPosition * (progressSlider.availableWidth - width)
                        y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                        width: progressSlider.pressed || progressSlider.hovered ? 18 : 0
                        height: width
                        radius: width / 2
                        color: Theme.text
                        
                        Behavior on width {
                            NumberAnimation { duration: Theme.animFast }
                        }
                    }
                    
                    onMoved: root.seek(value)
                }
                
                // Remaining time (negative format)
                Text {
                    text: "-" + formatTime(root.duration - root.position * root.duration)
                    font.pixelSize: Theme.fontSmall
                    font.family: "monospace"
                    font.weight: Font.Medium
                    color: Theme.textSecondary
                    Layout.preferredWidth: 55
                    horizontalAlignment: Text.AlignRight
                }
            }
        }
        
        Item { Layout.fillWidth: true }
        
        // === RIGHT: Volume & Extra Controls ===
        RowLayout {
            Layout.preferredWidth: 200
            spacing: Theme.spacingSmall
            
            // Toggle sidebar
            IconButton {
                iconPath: Icons.sidebar
                iconSize: 18
                buttonSize: 36
                highlighted: root.sidebarVisible
                tooltip: "Toggle sidebar (B)"
                
                onClicked: root.toggleSidebar()
            }
            
            // Volume icon
            IconButton {
                iconPath: root.volume === 0 ? Icons.volumeMute : (root.volume < 0.5 ? Icons.volumeLow : Icons.volumeHigh)
                iconSize: 18
                buttonSize: 36
                tooltip: "Toggle mute (M)"
                
                onClicked: root.toggleMute()
            }
            
            // Volume slider
            Slider {
                id: volumeSlider
                Layout.preferredWidth: 100
                from: 0
                to: 1
                value: root.volume
                
                background: Rectangle {
                    x: volumeSlider.leftPadding
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    width: volumeSlider.availableWidth
                    height: 4
                    radius: 2
                    color: Theme.border
                    
                    Rectangle {
                        width: volumeSlider.visualPosition * parent.width
                        height: parent.height
                        radius: 2
                        color: Theme.accent
                    }
                }
                
                handle: Rectangle {
                    x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    width: volumeSlider.pressed || volumeSlider.hovered ? 12 : 0
                    height: width
                    radius: width / 2
                    color: Theme.text
                    
                    Behavior on width {
                        NumberAnimation { duration: Theme.animFast }
                    }
                }
                
                onMoved: root.setVolume(value)
            }
        }
    }
    
    // Helper function
    function formatTime(seconds) {
        var mins = Math.floor(seconds / 60)
        var secs = Math.floor(seconds % 60)
        return mins + ":" + (secs < 10 ? "0" : "") + secs
    }
}
