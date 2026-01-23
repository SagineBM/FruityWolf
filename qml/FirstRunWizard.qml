import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Popup {
    id: wizard
    
    anchors.centerIn: parent
    width: 600
    height: 500
    modal: true
    closePolicy: Popup.NoAutoClose
    padding: 0
    
    property int currentStep: 0
    property var Theme
    
    signal completed()
    
    background: Rectangle {
        radius: 16
        color: Theme.backgroundLight
        border.width: 1
        border.color: Theme.border
    }
    
    contentItem: ColumnLayout {
        spacing: 0
        
        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            color: "transparent"
            
            // Gradient background
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.accent }
                    GradientStop { position: 1.0; color: Theme.accentDark }
                }
                opacity: 0.2
            }
            
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8
                
                SvgIcon {
                    iconName: Icons.music
                    size: 48
                    color: Theme.text
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Welcome to FL Library Pro"
                    font.pixelSize: 24
                    font.weight: Font.Bold
                    color: Theme.text
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
        
        // Step content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 32
            currentIndex: currentStep
            
            // Step 1: Introduction
            ColumnLayout {
                spacing: 24
                
                Text {
                    text: "Let's get you set up"
                    font.pixelSize: 20
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Text {
                    text: "FL Library Pro helps you organize, search, and play your FL Studio project renders with a beautiful Spotify-like interface."
                    font.pixelSize: 14
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                
                // Features list
                ColumnLayout {
                    spacing: 12
                    
                    FeatureItem {
                        iconName: Icons.music
                        text: "Instant in-app audio playback"
                        Theme: wizard.Theme
                    }
                    
                    FeatureItem {
                        iconName: Icons.search
                        text: "Fast search across all your projects"
                        Theme: wizard.Theme
                    }
                    
                    FeatureItem {
                        iconName: Icons.waveform
                        text: "BPM and Key detection"
                        Theme: wizard.Theme
                    }
                    
                    FeatureItem {
                        iconName: Icons.heart
                        text: "Favorites and playlists"
                        Theme: wizard.Theme
                    }
                }
                
                Item { Layout.fillHeight: true }
            }
            
            // Step 2: Select folder
            ColumnLayout {
                spacing: 24
                
                Text {
                    text: "Add your library folder"
                    font.pixelSize: 20
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Text {
                    text: "Select the folder containing your FL Studio projects. Each project should be in its own subfolder with rendered audio files."
                    font.pixelSize: 14
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                
                // Folder selector
                Rectangle {
                    Layout.fillWidth: true
                    height: 80
                    radius: 12
                    color: Theme.surface
                    border.width: 2
                    border.color: folderDropArea.containsDrag ? Theme.accent : Theme.border
                    border.pixelSize: folderDropArea.containsDrag ? 2 : 1
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 16
                        
                        SvgIcon {
                            iconName: Icons.folder
                            size: 32
                            color: Theme.textMuted
                        }
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            
                            Text {
                                id: selectedFolderText
                                text: "No folder selected"
                                font.pixelSize: 14
                                color: Theme.text
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                            }
                            
                            Text {
                                text: "Click to browse or drag & drop a folder"
                                font.pixelSize: 12
                                color: Theme.textMuted
                            }
                        }
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: folderDialog.open()
                    }
                    
                    DropArea {
                        id: folderDropArea
                        anchors.fill: parent
                        
                        onDropped: function(drop) {
                            if (drop.hasUrls) {
                                var path = drop.urls[0].toString().replace("file:///", "")
                                selectedFolderText.text = path
                            }
                        }
                    }
                }
                
                // Default folder suggestion
                Rectangle {
                    Layout.fillWidth: true
                    height: 60
                    radius: 8
                    color: Theme.surfaceHover
                    visible: true // Check if default folder exists
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12
                        
                        SvgIcon {
                            iconName: Icons.info
                            size: 20
                            color: Theme.accent
                        }
                        
                        Text {
                            text: "Use default: F:\\1.Project FL S1"
                            font.pixelSize: 13
                            color: Theme.text
                            Layout.fillWidth: true
                        }
                        
                        Button {
                            text: "Use This"
                            onClicked: {
                                selectedFolderText.text = "F:\\1.Project FL S1"
                            }
                        }
                    }
                }
                
                Item { Layout.fillHeight: true }
            }
            
            // Step 3: Scanning
            ColumnLayout {
                spacing: 24
                
                Text {
                    text: "Scanning your library..."
                    font.pixelSize: 20
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Text {
                    id: scanStatusText
                    text: "Looking for FL Studio projects..."
                    font.pixelSize: 14
                    color: Theme.textSecondary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                
                // Progress bar
                Rectangle {
                    Layout.fillWidth: true
                    height: 8
                    radius: 4
                    color: Theme.surfaceHover
                    
                    Rectangle {
                        id: scanProgressBar
                        width: parent.width * 0.3
                        height: parent.height
                        radius: 4
                        color: Theme.accent
                        
                        // Animation
                        SequentialAnimation on width {
                            running: currentStep === 2
                            loops: Animation.Infinite
                            
                            NumberAnimation {
                                from: 0
                                to: parent.width
                                duration: 1500
                                easing.type: Easing.InOutQuad
                            }
                            NumberAnimation {
                                from: parent.width
                                to: 0
                                duration: 0
                            }
                        }
                    }
                }
                
                // Stats
                GridLayout {
                    columns: 2
                    rowSpacing: 12
                    columnSpacing: 24
                    Layout.alignment: Qt.AlignHCenter
                    
                    Text {
                        text: "Projects found:"
                        font.pixelSize: 14
                        color: Theme.textSecondary
                    }
                    
                    Text {
                        id: projectsFoundText
                        text: "0"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: Theme.text
                    }
                    
                    Text {
                        text: "Tracks found:"
                        font.pixelSize: 14
                        color: Theme.textSecondary
                    }
                    
                    Text {
                        id: tracksFoundText
                        text: "0"
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        color: Theme.text
                    }
                }
                
                Item { Layout.fillHeight: true }
            }
            
            // Step 4: Complete
            ColumnLayout {
                spacing: 24
                
                Item { Layout.fillHeight: true }
                
                SvgIcon {
                    iconName: Icons.check
                    size: 64
                    color: Theme.success
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "You're all set!"
                    font.pixelSize: 24
                    font.weight: Font.Bold
                    color: Theme.text
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: "Your library is ready. Enjoy exploring your music!"
                    font.pixelSize: 14
                    color: Theme.textSecondary
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Item { Layout.fillHeight: true }
            }
        }
        
        // Footer with navigation
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: Theme.surface
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 24
                
                // Step indicators
                Row {
                    spacing: 8
                    
                    Repeater {
                        model: 4
                        
                        Rectangle {
                            width: currentStep === index ? 24 : 8
                            height: 8
                            radius: 4
                            color: currentStep >= index ? Theme.accent : Theme.surfaceHover
                            
                            Behavior on width { NumberAnimation { duration: 200 } }
                        }
                    }
                }
                
                Item { Layout.fillWidth: true }
                
                // Navigation buttons
                Button {
                    text: "Back"
                    visible: currentStep > 0 && currentStep < 3
                    flat: true
                    onClicked: currentStep--
                }
                
                Button {
                    text: currentStep === 0 ? "Get Started" : 
                          currentStep === 1 ? "Scan Library" :
                          currentStep === 2 ? "Please wait..." :
                          "Start Using FL Library Pro"
                    enabled: currentStep !== 2 && (currentStep !== 1 || selectedFolderText.text !== "No folder selected")
                    
                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 13
                        font.weight: Font.Bold
                        color: parent.enabled ? "#000000" : Theme.textMuted
                        horizontalAlignment: Text.AlignHCenter
                    }
                    
                    background: Rectangle {
                        color: parent.enabled ? (parent.hovered ? Theme.accentHover : Theme.accent) : Theme.surfaceHover
                        radius: 20
                    }
                    
                    onClicked: {
                        if (currentStep === 1) {
                            // Add folder and start scan
                            var path = selectedFolderText.text
                            if (path !== "No folder selected") {
                                backend.addLibraryRoot(path)
                                currentStep++
                                startScan()
                            }
                        } else if (currentStep === 3) {
                            wizard.completed()
                            wizard.close()
                        } else {
                            currentStep++
                        }
                    }
                }
            }
        }
    }
    
    // Feature item component
    component FeatureItem: RowLayout {
        property string iconName: ""
        property string text: ""
        property var Theme
        
        spacing: 12
        
        Rectangle {
            width: 40
            height: 40
            radius: 8
            color: Theme.surface
            
            SvgIcon {
                anchors.centerIn: parent
                iconName: parent.parent.iconName
                size: 20
                color: Theme.accent
            }
        }
        
        Text {
            text: parent.text
            font.pixelSize: 14
            color: Theme.textSecondary
            Layout.fillWidth: true
        }
    }
        
        Text {
            text: parent.text
            font.pixelSize: 14
            color: Theme.textSecondary
            Layout.fillWidth: true
        }
    }
    
    // Folder dialog
    FolderDialog {
        id: folderDialog
        title: "Select Library Folder"
        
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            selectedFolderText.text = path
        }
    }
    
    // Scan function
    function startScan() {
        backend.rescanLibrary()
    }
    
    // Connect to backend signals
    Connections {
        target: backend
        
        function onScanProgress(current, total, message) {
            if (currentStep === 2) {
                scanStatusText.text = message
                projectsFoundText.text = current.toString()
            }
        }
        
        function onScanFinished(projects, tracks) {
            if (currentStep === 2) {
                projectsFoundText.text = projects.toString()
                tracksFoundText.text = tracks.toString()
                currentStep = 3
            }
        }
    }
}
