import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "components"

ApplicationWindow {
    id: root
    visible: true
    width: 1400
    height: 900
    minimumWidth: 1000
    minimumHeight: 700
    title: appName + " v" + appVersion
    color: Theme.background

    // === STATE ===
    property string currentPage: "library"
    property var currentTrack: null
    property bool isPlaying: false
    property real playerPosition: 0
    property real playerDuration: 0
    property real playerVolume: 0.8
    property string repeatMode: "none"
    property bool shuffleEnabled: false
    property bool scanning: false
    property string scanMessage: ""
    property bool sidebarVisible: true
    property bool detailsPanelVisible: true
    property bool queueDrawerVisible: false
    property var queueTracks: []

    // === BACKEND CONNECTIONS ===
    Connections {
        target: backend
        
        function onPlayerStateChanged(state) {
            isPlaying = (state === "playing")
        }
        
        function onPlayerPositionChanged(pos) {
            if (!playerBar.seeking) {
                playerPosition = pos
            }
        }
        
        function onPlayerDurationChanged(dur) {
            playerDuration = dur
        }
        
        function onPlayerTrackChanged(track) {
            currentTrack = track
            if (track && track.path) {
                backend.loadWaveform(track.path)
            }
            // Update queue when track changes
            if (queueDrawerVisible) {
                updateQueue()
            }
        }
        
        function onPlayerVolumeChanged(vol) {
            playerVolume = vol
        }
        
        function onScanStarted() {
            scanning = true
        }
        
        function onScanProgress(current, total, message) {
            scanMessage = message + " (" + current + "/" + total + ")"
        }
        
        function onScanFinished(projects, tracks) {
            scanning = false
            scanMessage = ""
            backend.loadTracks()
        }
        
        function onWaveformReady(path, peaksMin, peaksMax) {
            if (currentTrack && currentTrack.path === path) {
                waveformView.setPeaks(peaksMin, peaksMax)
            }
        }
        
        function onQueueChanged() {
            if (queueDrawerVisible) {
                updateQueue()
            }
        }
    }

    // === KEYBOARD SHORTCUTS ===
    // Playback
    Shortcut { sequence: "Space"; onActivated: backend.togglePlay() }
    Shortcut { sequence: "Right"; onActivated: backend.nextTrack() }
    Shortcut { sequence: "Left"; onActivated: backend.previousTrack() }
    Shortcut { sequence: "Up"; onActivated: backend.setVolume(Math.min(1, playerVolume + 0.1)) }
    Shortcut { sequence: "Down"; onActivated: backend.setVolume(Math.max(0, playerVolume - 0.1)) }
    
    // Navigation
    Shortcut { sequence: "Ctrl+F"; onActivated: searchBar.focus() }
    Shortcut { sequence: "Ctrl+L"; onActivated: if (currentTrack) backend.toggleFavorite(currentTrack.id) }
    Shortcut { sequence: "Ctrl+1"; onActivated: setPage("library") }
    Shortcut { sequence: "Ctrl+2"; onActivated: setPage("favorites") }
    Shortcut { sequence: "Ctrl+3"; onActivated: setPage("playlists") }
    Shortcut { sequence: "Ctrl+4"; onActivated: setPage("settings") }
    
    // UI Controls  
    Shortcut { sequence: "B"; onActivated: sidebarVisible = !sidebarVisible }
    Shortcut { sequence: "D"; onActivated: detailsPanelVisible = !detailsPanelVisible }
    Shortcut { sequence: "Q"; onActivated: toggleQueueDrawer() }
    Shortcut { sequence: "/"; onActivated: searchBar.focus() }
    Shortcut { sequence: "F5"; onActivated: backend.rescanLibrary() }
    Shortcut { sequence: "Escape"; onActivated: { searchBar.text = ""; queueDrawerVisible = false } }
    
    // Player modes
    Shortcut { sequence: "S"; onActivated: toggleShuffle() }
    Shortcut { sequence: "R"; onActivated: cycleRepeat() }
    Shortcut { sequence: "M"; onActivated: backend.toggleMute() }
    
    // Track navigation
    Shortcut { sequence: "J"; onActivated: trackList.incrementCurrentIndex() }
    Shortcut { sequence: "K"; onActivated: trackList.decrementCurrentIndex() }
    Shortcut { sequence: "Return"; onActivated: if (trackList.currentIndex >= 0) playTrackAtIndex(trackList.currentIndex) }
    
    // Power user shortcuts
    Shortcut { 
        sequence: "Ctrl+Return"
        onActivated: if (currentTrack && currentTrack.flp_path) backend.openFlp(currentTrack.flp_path)
    }
    Shortcut { 
        sequence: "Alt+Return"
        onActivated: if (currentTrack && currentTrack.project_path) backend.openFolder(currentTrack.project_path)
    }
    Shortcut { 
        sequence: "Shift+Return"
        onActivated: {
            if (currentTrack) {
                backend.seek(0)
                backend.play()
            }
        }
    }

    function setPage(page) {
        currentPage = page
        if (page === "library") backend.loadTracks()
        else if (page === "favorites") backend.loadFavorites()
    }
    
    function toggleShuffle() {
        backend.toggleShuffle()
        shuffleEnabled = !shuffleEnabled
    }
    
    function cycleRepeat() {
        backend.cycleRepeat()
        if (repeatMode === "none") repeatMode = "all"
        else if (repeatMode === "all") repeatMode = "one"
        else repeatMode = "none"
    }
    
    function playTrackAtIndex(index) {
        var item = backend.filteredTrackModel.get(index)
        if (item) backend.playTrack(item.trackId)
    }
    
    function toggleQueueDrawer() {
        queueDrawerVisible = !queueDrawerVisible
        if (queueDrawerVisible) {
            updateQueue()
        }
    }
    
    function updateQueue() {
        queueTracks = backend.getQueue()
    }

    // === MAIN LAYOUT ===
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Content area
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // === SIDEBAR ===
            Rectangle {
                id: sidebar
                Layout.preferredWidth: sidebarVisible ? 260 : 0
                Layout.fillHeight: true
                color: Theme.backgroundLight
                clip: true
                
                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: Theme.animMedium; easing.type: Easing.OutCubic }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMedium
                    spacing: Theme.spacingSmall
                    visible: sidebarVisible

                    // Logo
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.spacingSmall
                        spacing: Theme.spacingMedium

                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMedium
                            gradient: Gradient {
                                orientation: Gradient.Vertical
                                GradientStop { position: 0.0; color: Theme.accent }
                                GradientStop { position: 1.0; color: Theme.accentDark }
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "FL"
                                font.pixelSize: 16
                                font.weight: Font.Black
                                color: Theme.background
                            }
                        }

                        ColumnLayout {
                            spacing: 0
                            Text {
                                text: "FL Library"
                                font.pixelSize: Theme.fontLarge
                                font.weight: Font.Bold
                                color: Theme.text
                            }
                            Text {
                                text: "Pro"
                                font.pixelSize: Theme.fontSmall
                                font.weight: Font.Medium
                                color: Theme.accent
                            }
                        }
                        
                        Item { Layout.fillWidth: true }
                    }

                    Item { Layout.preferredHeight: Theme.spacingLarge }

                    // Section label
                    Text {
                        text: "BROWSE"
                        font.pixelSize: Theme.fontXSmall
                        font.weight: Font.Bold
                        font.letterSpacing: 1.5
                        color: Theme.textMuted
                        Layout.leftMargin: Theme.spacingSmall
                    }
                    
                    Item { Layout.preferredHeight: Theme.spacingXSmall }

                    // Navigation
                    NavButton {
                        iconPath: Icons.library
                        text: "Library"
                        shortcut: "Ctrl+1"
                        selected: currentPage === "library"
                        onClicked: setPage("library")
                    }

                    NavButton {
                        iconPath: Icons.heart
                        text: "Favorites"
                        shortcut: "Ctrl+2"
                        selected: currentPage === "favorites"
                        onClicked: setPage("favorites")
                    }

                    NavButton {
                        iconPath: Icons.listMusic
                        text: "Playlists"
                        shortcut: "Ctrl+3"
                        selected: currentPage === "playlists"
                        onClicked: currentPage = "playlists"
                    }

                    NavButton {
                        iconPath: Icons.settings
                        text: "Settings"
                        shortcut: "Ctrl+4"
                        selected: currentPage === "settings"
                        onClicked: currentPage = "settings"
                    }

                    Item { Layout.preferredHeight: Theme.spacingLarge }
                    
                    // Playlists section
                    Text {
                        text: "PLAYLISTS"
                        font.pixelSize: Theme.fontXSmall
                        font.weight: Font.Bold
                        font.letterSpacing: 1.5
                        color: Theme.textMuted
                        Layout.leftMargin: Theme.spacingSmall
                    }
                    
                    Item { Layout.preferredHeight: Theme.spacingXSmall }

                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(contentHeight, 150)
                        clip: true
                        model: backend.playlistModel
                        spacing: 2
                        
                        delegate: NavButton {
                            width: parent ? parent.width : 0
                            iconPath: Icons.folder
                            text: model.name
                            selected: false
                            onClicked: {
                                currentPage = "playlist"
                            }
                        }
                    }

                    // Create playlist button
                    Rectangle {
                        Layout.fillWidth: true
                        height: 40
                        radius: Theme.radiusMedium
                        color: createPlaylistMouse.containsMouse ? Theme.surfaceHover : "transparent"
                        
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spacingMedium
                            spacing: Theme.spacingMedium
                            
                            SvgIcon {
                                pathData: Icons.plus
                                size: 18
                                color: Theme.textMuted
                            }
                            
                            Text {
                                text: "Create Playlist"
                                font.pixelSize: Theme.fontMedium
                                color: Theme.textSecondary
                            }
                        }
                        
                        MouseArea {
                            id: createPlaylistMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: createPlaylistDialog.open()
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Library section
                    Text {
                        text: "LIBRARY"
                        font.pixelSize: Theme.fontXSmall
                        font.weight: Font.Bold
                        font.letterSpacing: 1.5
                        color: Theme.textMuted
                        Layout.leftMargin: Theme.spacingSmall
                    }
                    
                    Item { Layout.preferredHeight: Theme.spacingXSmall }

                    // Rescan button
                    Rectangle {
                        Layout.fillWidth: true
                        height: 44
                        radius: Theme.radiusRound
                        enabled: !scanning
                        opacity: enabled ? 1 : 0.6
                        
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: rescanMouse.containsMouse && !scanning ? Theme.accentHover : Theme.accent }
                            GradientStop { position: 1.0; color: rescanMouse.containsMouse && !scanning ? Theme.accent : Theme.accentDark }
                        }
                        
                        RowLayout {
                            anchors.centerIn: parent
                            spacing: Theme.spacingSmall
                            
                            SvgIcon {
                                pathData: Icons.refresh
                                size: 16
                                color: Theme.background
                                
                                RotationAnimation on rotation {
                                    running: scanning
                                    loops: Animation.Infinite
                                    from: 0
                                    to: 360
                                    duration: 1000
                                }
                            }
                            
                            Text {
                                text: scanning ? "Scanning..." : "Rescan Library"
                                font.pixelSize: Theme.fontSmall
                                font.weight: Font.Bold
                                color: Theme.background
                            }
                        }
                        
                        MouseArea {
                            id: rescanMouse
                            anchors.fill: parent
                            hoverEnabled: !scanning
                            cursorShape: scanning ? Qt.WaitCursor : Qt.PointingHandCursor
                            onClicked: if (!scanning) backend.rescanLibrary()
                        }
                    }

                    // Scan status
                    Text {
                        visible: scanning
                        text: scanMessage
                        font.pixelSize: Theme.fontXSmall
                        color: Theme.textMuted
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                        horizontalAlignment: Text.AlignHCenter
                    }
                    
                    Item { Layout.preferredHeight: Theme.spacingSmall }
                }
            }

            // Sidebar divider
            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Theme.border
                visible: sidebarVisible
            }

            // === MAIN CONTENT ===
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.background

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingLarge
                    spacing: Theme.spacingMedium

                    // Header with search
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMedium

                        SearchBar {
                            id: searchBar
                            Layout.fillWidth: true
                            Layout.maximumWidth: 500
                            
                            onSearch: function(query) {
                                backend.filteredTrackModel.setSearchText(query)
                            }
                            
                            onCleared: {
                                backend.filteredTrackModel.clearFilters()
                            }
                        }

                        Item { Layout.fillWidth: true }

                        // Filter buttons
                        FilterChip {
                            text: "BPM"
                            iconPath: Icons.barChart
                            onClicked: bpmFilterPopup.open()
                        }

                        FilterChip {
                            text: "Key"
                            iconPath: Icons.music
                            onClicked: keyFilterPopup.open()
                        }

                        FilterChip {
                            text: "Favorites"
                            iconPath: Icons.heart
                            checkable: true
                            onToggled: function(checked) {
                                backend.filteredTrackModel.setFavoritesOnly(checked)
                            }
                        }
                    }

                    // Track count & sort
                    RowLayout {
                        Layout.fillWidth: true
                        
                        Text {
                            text: backend.filteredTrackModel.rowCount() + " tracks"
                            font.pixelSize: Theme.fontSmall
                            color: Theme.textMuted
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        // Keyboard hint
                        Row {
                            spacing: Theme.spacingSmall
                            opacity: 0.6
                            
                            Text {
                                text: "Navigate:"
                                font.pixelSize: Theme.fontXSmall
                                color: Theme.textMuted
                            }
                            
                            KeyHint { text: "J/K" }
                            
                            Text {
                                text: "Play:"
                                font.pixelSize: Theme.fontXSmall
                                color: Theme.textMuted
                            }
                            
                            KeyHint { text: "Enter" }
                        }
                    }

                    // Track list
                    ListView {
                        id: trackList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: backend.filteredTrackModel
                        spacing: 2
                        focus: true
                        keyNavigationEnabled: true

                        ScrollBar.vertical: ScrollBar {
                            active: true
                            policy: ScrollBar.AsNeeded
                        }

                        delegate: TrackItem {
                            width: trackList.width - 16
                            track: model
                            isPlaying: currentTrack && currentTrack.id === model.trackId && root.isPlaying
                            isSelected: trackList.currentIndex === index
                            
                            onClicked: {
                                trackList.currentIndex = index
                            }
                            
                            onDoubleClicked: {
                                backend.playTrack(model.trackId)
                            }
                            
                            onPlayClicked: {
                                backend.playTrack(model.trackId)
                            }
                            
                            onFavoriteClicked: {
                                backend.toggleFavorite(model.trackId)
                            }
                        }

                        // Empty state
                        Column {
                            anchors.centerIn: parent
                            visible: trackList.count === 0
                            spacing: Theme.spacingMedium
                            
                            SvgIcon {
                                anchors.horizontalCenter: parent.horizontalCenter
                                pathData: Icons.music
                                size: 64
                                color: Theme.textMuted
                                opacity: 0.5
                            }
                            
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: scanning ? "Scanning library..." : "No tracks found"
                                font.pixelSize: Theme.fontLarge
                                color: Theme.textSecondary
                            }
                            
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: scanning ? "Please wait..." : "Add a library folder in settings or click 'Rescan Library'"
                                font.pixelSize: Theme.fontMedium
                                color: Theme.textMuted
                            }
                        }
                    }
                }
            }

            // Details divider
            Rectangle {
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                color: Theme.border
                visible: detailsPanelVisible && currentTrack
            }

            // === DETAILS PANEL ===
            Rectangle {
                id: detailsPanel
                Layout.preferredWidth: (detailsPanelVisible && currentTrack) ? 340 : 0
                Layout.fillHeight: true
                color: Theme.backgroundLight
                clip: true

                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: Theme.animMedium; easing.type: Easing.OutCubic }
                }

                visible: Layout.preferredWidth > 0

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacingMedium
                    spacing: Theme.spacingMedium

                    // Waveform / Cover
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        radius: Theme.radiusLarge
                        color: Theme.surface

                        WaveformView {
                            id: waveformView
                            anchors.fill: parent
                            anchors.margins: Theme.spacingSmall
                            position: playerPosition
                            
                            onSeek: function(pos) {
                                backend.seek(pos)
                            }
                        }

                        // Gradient overlay
                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.08) }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                        }
                    }

                    // Track title
                    Text {
                        text: currentTrack ? currentTrack.title : ""
                        font.pixelSize: Theme.fontXLarge
                        font.weight: Font.Bold
                        color: Theme.text
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    // Project name
                    Text {
                        text: currentTrack ? currentTrack.project_name : ""
                        font.pixelSize: Theme.fontMedium
                        color: Theme.textSecondary
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }

                    // Metadata grid
                    GridLayout {
                        columns: 2
                        columnSpacing: Theme.spacingMedium
                        rowSpacing: Theme.spacingSmall
                        Layout.fillWidth: true

                        MetadataItem {
                            label: "BPM"
                            value: currentTrack ? backend.formatBpm(currentTrack.bpm_user || currentTrack.bpm_detected || 0) : "--"
                            accentColor: Theme.accent
                        }

                        MetadataItem {
                            label: "Key"
                            value: currentTrack ? backend.formatKey(currentTrack.key_user || currentTrack.key_detected || "") : "--"
                            accentColor: Theme.secondary
                        }

                        MetadataItem {
                            label: "Duration"
                            value: currentTrack ? backend.formatDuration(currentTrack.duration || 0) : "--"
                        }

                        MetadataItem {
                            label: "Size"
                            value: currentTrack ? backend.formatFileSize(currentTrack.file_size || 0) : "--"
                        }
                    }

                    // Divider
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Actions - Grouped by workflow
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spacingMedium

                        // === PLAYBACK (Primary) ===
                        Rectangle {
                            Layout.fillWidth: true
                            height: 48
                            radius: Theme.radiusMedium
                            visible: currentTrack !== null
                            
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: playRenderMouse.containsPress ? Theme.accentDark : (playRenderMouse.containsMouse ? Theme.accent : Theme.accentMuted) }
                                GradientStop { position: 1.0; color: playRenderMouse.containsPress ? Theme.accent : (playRenderMouse.containsMouse ? Theme.accentHover : Theme.accent) }
                            }
                            
                            RowLayout {
                                anchors.centerIn: parent
                                spacing: Theme.spacingSmall
                                
                                SvgIcon {
                                    pathData: Icons.play
                                    size: 18
                                    color: Theme.background
                                    filled: true
                                }
                                
                                Text {
                                    text: "Play Render"
                                    font.pixelSize: Theme.fontMedium
                                    font.weight: Font.Bold
                                    color: Theme.background
                                }
                            }
                            
                            MouseArea {
                                id: playRenderMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: if (currentTrack) backend.playTrack(currentTrack.id)
                            }
                        }
                        
                        // === PROJECT ===
                        Text {
                            text: "PROJECT"
                            font.pixelSize: Theme.fontXSmall
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                            color: Theme.textMuted
                            Layout.topMargin: Theme.spacingSmall
                        }
                        
                        Row {
                            Layout.fillWidth: true
                            spacing: Theme.spacingSmall
                            
                            // Open Folder
                            Rectangle {
                                width: (parent.width - Theme.spacingSmall) / 2
                                height: 40
                                radius: Theme.radiusSmall
                                color: folderMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                                
                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: Theme.spacingXSmall
                                    
                                    SvgIcon {
                                        pathData: Icons.folder
                                        size: 16
                                        color: Theme.textSecondary
                                    }
                                    
                                    Text {
                                        text: "Folder"
                                        font.pixelSize: Theme.fontSmall
                                        color: Theme.text
                                    }
                                }
                                
                                MouseArea {
                                    id: folderMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (currentTrack) backend.openFolder(currentTrack.project_path)
                                }
                            }
                            
                            // Open FLP
                            Rectangle {
                                width: (parent.width - Theme.spacingSmall) / 2
                                height: 40
                                radius: Theme.radiusSmall
                                color: flpMouse.containsMouse ? Theme.surfaceHover : Theme.surface
                                opacity: currentTrack && currentTrack.flp_path ? 1 : 0.4
                                
                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: Theme.spacingXSmall
                                    
                                    SvgIcon {
                                        pathData: Icons.piano
                                        size: 16
                                        color: Theme.secondary
                                    }
                                    
                                    Text {
                                        text: "FLP"
                                        font.pixelSize: Theme.fontSmall
                                        color: Theme.text
                                    }
                                }
                                
                                MouseArea {
                                    id: flpMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: currentTrack && currentTrack.flp_path ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: if (currentTrack && currentTrack.flp_path) backend.openFlp(currentTrack.flp_path)
                                }
                            }
                        }
                        
                        // === ANALYZE ===
                        Text {
                            text: "ANALYZE"
                            font.pixelSize: Theme.fontXSmall
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                            color: Theme.textMuted
                            Layout.topMargin: Theme.spacingSmall
                        }
                        
                        ActionButton {
                            iconPath: Icons.sparkles
                            text: "Detect BPM & Key"
                            onClicked: if (currentTrack) backend.analyzeTrack(currentTrack.id, currentTrack.path)
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }

        // === QUEUE DRAWER (bottom drawer) ===
        QueueDrawer {
            id: queueDrawer
            Layout.fillWidth: true
            Layout.preferredHeight: queueDrawerVisible ? 280 : 0
            
            visible: queueDrawerVisible
            clip: true
            
            queueModel: root.queueTracks
            currentTrack: root.currentTrack
            isPlaying: root.isPlaying
            
            Behavior on Layout.preferredHeight {
                NumberAnimation { duration: Theme.animMedium; easing.type: Easing.OutCubic }
            }
            
            onPlayTrack: function(trackId) {
                backend.playTrack(trackId)
            }
            
            onRemoveFromQueue: function(trackId) {
                backend.removeFromQueue(trackId)
            }
            
            onClearQueue: {
                backend.clearQueue()
            }
            
            onClose: {
                queueDrawerVisible = false
            }
        }

        // === PLAYER BAR ===
        PlayerBar {
            id: playerBar
            Layout.fillWidth: true
            
            currentTrack: root.currentTrack
            isPlaying: root.isPlaying
            position: root.playerPosition
            duration: root.playerDuration
            volume: root.playerVolume
            repeatMode: root.repeatMode
            shuffleEnabled: root.shuffleEnabled
            sidebarVisible: root.sidebarVisible
            
            property bool seeking: false
            
            onTogglePlay: backend.togglePlay()
            onNextTrack: backend.nextTrack()
            onPreviousTrack: backend.previousTrack()
            onSeek: function(pos) { backend.seek(pos) }
            onSetVolume: function(vol) { backend.setVolume(vol) }
            onToggleMute: backend.toggleMute()
            onToggleShuffle: root.toggleShuffle()
            onCycleRepeat: root.cycleRepeat()
            onToggleSidebar: root.sidebarVisible = !root.sidebarVisible
            onToggleFavorite: if (currentTrack) backend.toggleFavorite(currentTrack.id)
        }
    }

    // === INLINE COMPONENTS ===
    
    component FilterChip: Rectangle {
        property string text: ""
        property string iconPath: ""
        property bool checkable: false
        property bool checked: false
        
        signal clicked()
        signal toggled(bool checked)
        
        width: chipRow.implicitWidth + Theme.spacingLarge
        height: 36
        radius: Theme.radiusRound
        color: checked ? Theme.accentGlow : (chipMouse.containsMouse ? Theme.surfaceHover : Theme.surface)
        border.width: 1
        border.color: checked ? Theme.accent : Theme.border
        
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
        Behavior on border.color { ColorAnimation { duration: Theme.animFast } }
        
        Row {
            id: chipRow
            anchors.centerIn: parent
            spacing: Theme.spacingXSmall
            
            SvgIcon {
                visible: iconPath
                pathData: iconPath
                size: 14
                color: checked ? Theme.accent : Theme.textSecondary
            }
            
            Text {
                text: parent.parent.text
                font.pixelSize: Theme.fontSmall
                color: checked ? Theme.accent : Theme.textSecondary
            }
        }
        
        MouseArea {
            id: chipMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (checkable) {
                    checked = !checked
                    parent.toggled(checked)
                } else {
                    parent.clicked()
                }
            }
        }
    }
    
    component KeyHint: Rectangle {
        property string text: ""
        width: hintText.implicitWidth + 8
        height: 18
        radius: 4
        color: Theme.glassBg
        border.width: 1
        border.color: Theme.glassBorder
        
        Text {
            id: hintText
            anchors.centerIn: parent
            text: parent.text
            font.pixelSize: 10
            font.family: "monospace"
            color: Theme.textMuted
        }
    }
    
    component MetadataItem: ColumnLayout {
        property string label: ""
        property string value: ""
        property color accentColor: Theme.text
        
        spacing: 4
        Layout.fillWidth: true
        
        Text {
            text: label
            font.pixelSize: Theme.fontXSmall
            font.weight: Font.Medium
            font.letterSpacing: 0.5
            color: Theme.textMuted
            textFormat: Text.PlainText
        }
        
        Text {
            text: value
            font.pixelSize: Theme.fontXLarge
            font.weight: Font.Bold
            color: accentColor
        }
    }
    
    component ActionButton: Rectangle {
        property string iconPath: ""
        property string text: ""
        signal clicked()
        
        Layout.fillWidth: true
        height: 44
        radius: Theme.radiusMedium
        color: actionMouse.containsMouse ? Theme.surfaceHover : Theme.surface
        
        Behavior on color { ColorAnimation { duration: Theme.animFast } }
        
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacingMedium
            anchors.rightMargin: Theme.spacingMedium
            spacing: Theme.spacingMedium
            
            SvgIcon {
                pathData: iconPath
                size: 18
                color: Theme.textSecondary
            }
            
            Text {
                Layout.fillWidth: true
                text: parent.parent.text
                font.pixelSize: Theme.fontMedium
                color: Theme.text
            }
            
            SvgIcon {
                pathData: Icons.externalLink
                size: 14
                color: Theme.textMuted
                opacity: actionMouse.containsMouse ? 1 : 0
                
                Behavior on opacity { NumberAnimation { duration: Theme.animFast } }
            }
        }
        
        MouseArea {
            id: actionMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    component WaveformView: Item {
        id: waveformRoot
        property real position: 0
        property var peaksMin: []
        property var peaksMax: []
        
        signal seek(real pos)
        
        function setPeaks(min, max) {
            peaksMin = min
            peaksMax = max
            canvas.requestPaint()
        }
        
        Canvas {
            id: canvas
            anchors.fill: parent
            
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                
                if (waveformRoot.peaksMin.length === 0) {
                    ctx.fillStyle = Theme.surfaceHover
                    ctx.fillRect(0, height * 0.3, width, height * 0.4)
                    return
                }
                
                var centerY = height / 2
                var samples = waveformRoot.peaksMin.length
                var step = width / samples
                
                // Draw waveform with gradient
                var gradient = ctx.createLinearGradient(0, 0, width, 0)
                gradient.addColorStop(0, Theme.accent)
                gradient.addColorStop(0.5, Theme.accentHover)
                gradient.addColorStop(1, Theme.secondary)
                ctx.fillStyle = gradient
                
                for (var i = 0; i < samples; i++) {
                    var x = i * step
                    var minVal = waveformRoot.peaksMin[i] * centerY
                    var maxVal = waveformRoot.peaksMax[i] * centerY
                    ctx.fillRect(x, centerY - maxVal, step - 1, maxVal - minVal)
                }
            }
        }
        
        // Playhead
        Rectangle {
            x: position * parent.width - 1
            y: 0
            width: 2
            height: parent.height
            color: Theme.text
            visible: waveformRoot.peaksMin.length > 0
            
            // Glow
            Rectangle {
                anchors.centerIn: parent
                width: 6
                height: parent.height
                color: Theme.accentGlow
                opacity: 0.5
            }
        }
        
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: function(mouse) {
                var pos = mouse.x / width
                waveformRoot.seek(pos)
            }
        }
        
        onPositionChanged: canvas.requestPaint()
    }

    // === DIALOGS ===
    Dialog {
        id: createPlaylistDialog
        title: "Create Playlist"
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        modal: true
        
        contentItem: ColumnLayout {
            spacing: Theme.spacingMedium
            
            TextField {
                id: playlistNameInput
                Layout.fillWidth: true
                placeholderText: "Playlist name"
            }
        }
        
        onAccepted: {
            if (playlistNameInput.text) {
                backend.createPlaylist(playlistNameInput.text)
                playlistNameInput.text = ""
            }
        }
    }

    // BPM Filter popup
    Popup {
        id: bpmFilterPopup
        x: parent.width / 2 - width / 2
        y: 100
        width: 300
        padding: Theme.spacingMedium
        modal: true
        
        background: Rectangle {
            color: Theme.surface
            radius: Theme.radiusLarge
            border.color: Theme.border
        }
        
        contentItem: ColumnLayout {
            spacing: Theme.spacingMedium
            
            Text {
                text: "BPM Range"
                font.pixelSize: Theme.fontMedium
                font.weight: Font.Bold
                color: Theme.text
            }
            
            RowLayout {
                spacing: Theme.spacingMedium
                
                TextField {
                    id: bpmMinInput
                    Layout.fillWidth: true
                    placeholderText: "Min"
                }
                
                Text {
                    text: "—"
                    color: Theme.textSecondary
                }
                
                TextField {
                    id: bpmMaxInput
                    Layout.fillWidth: true
                    placeholderText: "Max"
                }
            }
            
            RowLayout {
                spacing: Theme.spacingSmall
                
                Button {
                    text: "Apply"
                    onClicked: {
                        var min = parseFloat(bpmMinInput.text) || 0
                        var max = parseFloat(bpmMaxInput.text) || 0
                        backend.filteredTrackModel.setBpmRange(min, max)
                        bpmFilterPopup.close()
                    }
                }
                
                Button {
                    text: "Clear"
                    flat: true
                    onClicked: {
                        bpmMinInput.text = ""
                        bpmMaxInput.text = ""
                        backend.filteredTrackModel.setBpmRange(0, 0)
                        bpmFilterPopup.close()
                    }
                }
            }
        }
    }

    // Key Filter popup
    Popup {
        id: keyFilterPopup
        x: parent.width / 2 - width / 2
        y: 100
        width: 380
        padding: Theme.spacingMedium
        modal: true
        
        background: Rectangle {
            color: Theme.surface
            radius: Theme.radiusLarge
            border.color: Theme.border
        }
        
        contentItem: ColumnLayout {
            spacing: Theme.spacingMedium
            
            Text {
                text: "Musical Key"
                font.pixelSize: Theme.fontMedium
                font.weight: Font.Bold
                color: Theme.text
            }
            
            GridLayout {
                columns: 6
                rowSpacing: Theme.spacingSmall
                columnSpacing: Theme.spacingSmall
                
                Repeater {
                    model: backend.getAvailableKeys()
                    
                    Rectangle {
                        width: 52
                        height: 36
                        radius: Theme.radiusMedium
                        color: keyItemMouse.containsMouse ? Theme.surfaceActive : Theme.surfaceHover
                        
                        Text {
                            anchors.centerIn: parent
                            text: modelData
                            font.pixelSize: Theme.fontSmall
                            color: Theme.text
                        }
                        
                        MouseArea {
                            id: keyItemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                backend.filteredTrackModel.setKeyFilter(modelData)
                                keyFilterPopup.close()
                            }
                        }
                    }
                }
            }
            
            Button {
                text: "Clear Filter"
                flat: true
                onClicked: {
                    backend.filteredTrackModel.setKeyFilter("")
                    keyFilterPopup.close()
                }
            }
        }
    }

    // Load tracks on start
    Component.onCompleted: {
        backend.loadTracks()
    }
}
