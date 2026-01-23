import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: playlistPage
    
    property var playlist: null
    property var Theme
    property var tracks: []
    
    signal backClicked()
    signal playTrack(var track)
    signal playAll()
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 24
        
        // Header with cover art
        RowLayout {
            Layout.fillWidth: true
            spacing: 24
            
            // Cover art
            Rectangle {
                width: 200
                height: 200
                radius: 8
                color: Theme.surfaceHover
                
                // Gradient pattern
                gradient: Gradient {
                    GradientStop { position: 0.0; color: playlist ? Qt.hsla((playlist.name.charCodeAt(0) % 360) / 360, 0.6, 0.4, 1) : Theme.surfaceHover }
                    GradientStop { position: 1.0; color: playlist ? Qt.hsla(((playlist.name.charCodeAt(0) + 60) % 360) / 360, 0.5, 0.3, 1) : Theme.surfaceHover }
                }
                
                // Grid pattern for collage effect
                Grid {
                    anchors.fill: parent
                    columns: 2
                    visible: tracks.length >= 4
                    
                    Repeater {
                        model: Math.min(tracks.length, 4)
                        
                        Rectangle {
                            width: 100
                            height: 100
                            
                            gradient: Gradient {
                                GradientStop { 
                                    position: 0.0
                                    color: tracks[index] ? Qt.hsla((tracks[index].title.charCodeAt(0) % 360) / 360, 0.6, 0.4, 1) : Theme.surface
                                }
                                GradientStop { 
                                    position: 1.0
                                    color: tracks[index] ? Qt.hsla(((tracks[index].title.charCodeAt(0) + 40) % 360) / 360, 0.5, 0.3, 1) : Theme.surface
                                }
                            }
                            
                            Text {
                                anchors.centerIn: parent
                                text: tracks[index] ? tracks[index].title.charAt(0).toUpperCase() : ""
                                font.pixelSize: 32
                                font.weight: Font.Bold
                                color: Qt.rgba(1, 1, 1, 0.8)
                            }
                        }
                    }
                }
                
                // Playlist icon for small playlists
                SvgIcon {
                    anchors.centerIn: parent
                    iconName: Icons.listMusic
                    size: 64
                    color: Qt.rgba(1, 1, 1, 0.3)
                    visible: tracks.length < 4
                }
            }
            
            // Playlist info
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                
                Text {
                    text: "PLAYLIST"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    color: Theme.textSecondary
                }
                
                Text {
                    text: playlist ? playlist.name : "Untitled Playlist"
                    font.pixelSize: 48
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Text {
                    text: playlist ? (playlist.description || "") : ""
                    font.pixelSize: 14
                    color: Theme.textSecondary
                    visible: text !== ""
                }
                
                Text {
                    text: tracks.length + " tracks"
                    font.pixelSize: 14
                    color: Theme.textMuted
                }
                
                Item { Layout.preferredHeight: 16 }
                
                // Action buttons
                RowLayout {
                    spacing: 16
                    
                    // Play button
                    Rectangle {
                        width: 56
                        height: 56
                        radius: 28
                        color: Theme.accent
                        
                        SvgIcon {
                            anchors.centerIn: parent
                            iconName: Icons.play
                            size: 24
                            color: "#000000"
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: playlistPage.playAll()
                        }
                        
                        scale: playAllMouse.containsMouse ? 1.05 : 1
                        Behavior on scale { NumberAnimation { duration: 100 } }
                        
                        MouseArea {
                            id: playAllMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: playlistPage.playAll()
                        }
                    }
                    
                    // Shuffle button
                    Rectangle {
                        width: 44
                        height: 44
                        radius: 22
                        color: "transparent"
                        border.width: 1
                        border.color: Theme.textSecondary
                        
                        SvgIcon {
                            anchors.centerIn: parent
                            iconName: Icons.shuffle
                            size: 18
                            color: Theme.textSecondary
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                backend.toggleShuffle()
                                playlistPage.playAll()
                            }
                        }
                    }
                    
                    // More options
                    Rectangle {
                        width: 44
                        height: 44
                        radius: 22
                        color: "transparent"
                        
                        Text {
                            anchors.centerIn: parent
                            text: "⋮"
                            font.pixelSize: 24
                            color: Theme.textSecondary
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: playlistMenu.open()
                        }
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            // Back button
            Text {
                text: "✕"
                font.pixelSize: 24
                color: Theme.textSecondary
                Layout.alignment: Qt.AlignTop
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: playlistPage.backClicked()
                }
            }
        }
        
        // Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        
        // Track list header
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            spacing: 16
            
            Text {
                text: "#"
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.preferredWidth: 40
            }
            
            Text {
                text: "TITLE"
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.fillWidth: true
            }
            
            Text {
                text: "BPM"
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.preferredWidth: 60
            }
            
            Text {
                text: "KEY"
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.preferredWidth: 60
            }
            
            Text {
                text: "DURATION"
                font.pixelSize: 12
                color: Theme.textMuted
                Layout.preferredWidth: 80
            }
        }
        
        // Track list
        ListView {
            id: trackList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: tracks
            spacing: 2
            
            ScrollBar.vertical: ScrollBar { active: true }
            
            delegate: PlaylistTrackItem {
                width: trackList.width
                index: model.index + 1
                track: modelData
                Theme: playlistPage.Theme
                
                onClicked: playlistPage.playTrack(modelData)
                onRemoveClicked: {
                    if (playlist) {
                        backend.removeTrackFromPlaylist(playlist.id, modelData.id)
                        tracks = backend.getPlaylistTracks(playlist.id)
                    }
                }
            }
            
            // Empty state
            Text {
                anchors.centerIn: parent
                visible: trackList.count === 0
                text: "This playlist is empty\n\nDrag tracks here or use the context menu"
                font.pixelSize: 16
                color: Theme.textMuted
                horizontalAlignment: Text.AlignHCenter
            }
            
            // Drop area for drag and drop
            DropArea {
                anchors.fill: parent
                
                onDropped: function(drop) {
                    if (drop.hasText && playlist) {
                        var trackId = parseInt(drop.text)
                        backend.addTrackToPlaylist(playlist.id, trackId)
                        tracks = backend.getPlaylistTracks(playlist.id)
                    }
                }
            }
        }
    }
    
    // Playlist context menu
    Menu {
        id: playlistMenu
        
        MenuItem {
            text: "Rename Playlist"
            onTriggered: renameDialog.open()
        }
        
        MenuItem {
            text: "Export as M3U"
            onTriggered: {
                // Export playlist
            }
        }
        
        MenuSeparator {}
        
        MenuItem {
            text: "Delete Playlist"
            onTriggered: deleteConfirmDialog.open()
        }
    }
    
    // Rename dialog
    Dialog {
        id: renameDialog
        title: "Rename Playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        modal: true
        
        contentItem: TextField {
            id: renameInput
            text: playlist ? playlist.name : ""
            placeholderText: "Playlist name"
        }
        
        onAccepted: {
            if (renameInput.text && playlist) {
                backend.renamePlaylist(playlist.id, renameInput.text)
                playlist.name = renameInput.text
            }
        }
    }
    
    // Delete confirmation
    Dialog {
        id: deleteConfirmDialog
        title: "Delete Playlist?"
        standardButtons: Dialog.Yes | Dialog.No
        anchors.centerIn: parent
        modal: true
        
        contentItem: Text {
            text: "Are you sure you want to delete this playlist?\nThis action cannot be undone."
            color: Theme.text
        }
        
        onAccepted: {
            if (playlist) {
                backend.deletePlaylist(playlist.id)
                playlistPage.backClicked()
            }
        }
    }
    
    // Playlist track item component
    component PlaylistTrackItem: Rectangle {
        id: trackItem
        
        property int index: 0
        property var track
        property var Theme
        
        signal clicked()
        signal removeClicked()
        
        height: 56
        radius: 8
        color: trackMouseArea.containsMouse ? Theme.surfaceHover : "transparent"
        
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 16
            
            // Track number / Play button
            Item {
                width: 40
                height: 40
                
                Text {
                    anchors.centerIn: parent
                    visible: !trackMouseArea.containsMouse
                    text: index.toString()
                    font.pixelSize: 14
                    color: Theme.textMuted
                }
                
                SvgIcon {
                    anchors.centerIn: parent
                    visible: trackMouseArea.containsMouse
                    iconName: Icons.play
                    size: 14
                    color: Theme.accent
                }
            }
            
            // Track info
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                
                Text {
                    text: track ? track.title : ""
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    color: Theme.text
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                
                Text {
                    text: track ? track.project_name : ""
                    font.pixelSize: 12
                    color: Theme.textSecondary
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
            
            // BPM
            Text {
                text: track && track.bpm ? Math.round(track.bpm).toString() : "--"
                font.pixelSize: 13
                color: Theme.textMuted
                Layout.preferredWidth: 60
            }
            
            // Key
            Text {
                text: track && track.key ? track.key : "--"
                font.pixelSize: 13
                color: Theme.textMuted
                Layout.preferredWidth: 60
            }
            
            // Duration
            Text {
                text: track ? backend.formatDuration(track.duration || 0) : "--"
                font.pixelSize: 13
                color: Theme.textMuted
                Layout.preferredWidth: 80
            }
            
            // Remove button
            SvgIcon {
                iconName: Icons.x
                size: 14
                color: Theme.textMuted
                visible: trackMouseArea.containsMouse
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: trackItem.removeClicked()
                }
            }
        }
        
        MouseArea {
            id: trackMouseArea
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton
            
            onClicked: trackItem.clicked()
            onDoubleClicked: trackItem.clicked()
        }
        
        // Drag handle for reordering
        Drag.active: dragArea.drag.active
        Drag.hotSpot.x: width / 2
        Drag.hotSpot.y: height / 2
        
        MouseArea {
            id: dragArea
            width: 20
            height: parent.height
            anchors.left: parent.left
            drag.target: parent
            cursorShape: Qt.DragMoveCursor
        }
    }
    
    // Load tracks when playlist changes
    onPlaylistChanged: {
        if (playlist) {
            tracks = backend.getPlaylistTracks(playlist.id)
        } else {
            tracks = []
        }
    }
}
