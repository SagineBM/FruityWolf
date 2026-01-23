import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: settingsPage
    
    // Theme reference (should come from parent)
    property var Theme: parent.Theme
    
    signal backClicked()
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 24
        
        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            
            Text {
                text: "←"
                font.pixelSize: 24
                color: Theme.text
                
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: settingsPage.backClicked()
                }
            }
            
            Text {
                text: "Settings"
                font.pixelSize: 28
                font.weight: Font.Bold
                color: Theme.text
            }
        }
        
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ColumnLayout {
                width: parent.width
                spacing: 32
                
                // Library section
                SettingsSection {
                    title: "Library"
                    
                    ColumnLayout {
                        spacing: 16
                        Layout.fillWidth: true
                        
                        // Library roots
                        Text {
                            text: "Library Folders"
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            color: Theme.text
                        }
                        
                        Text {
                            text: "Add folders containing your FL Studio projects"
                            font.pixelSize: 12
                            color: Theme.textSecondary
                        }
                        
                        ListView {
                            id: libraryRootsList
                            Layout.fillWidth: true
                            Layout.preferredHeight: contentHeight
                            model: backend.getLibraryRoots()
                            spacing: 8
                            
                            delegate: Rectangle {
                                width: libraryRootsList.width
                                height: 48
                                radius: 8
                                color: Theme.surfaceHover
                                
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    
                                    SvgIcon {
                                        iconName: Icons.folder
                                        size: 16
                                        color: Theme.text
                                    }
                                    
                                    Text {
                                        text: modelData
                                        font.pixelSize: 13
                                        color: Theme.text
                                        Layout.fillWidth: true
                                        elide: Text.ElideMiddle
                                    }
                                    
                                    Text {
                                        text: "✕"
                                        font.pixelSize: 14
                                        color: Theme.textMuted
                                        
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                // Remove library root
                                                // backend.removeLibraryRoot(modelData)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        Button {
                            text: "+ Add Folder"
                            onClicked: folderDialog.open()
                            
                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 13
                                color: Theme.accent
                            }
                            
                            background: Rectangle {
                                color: "transparent"
                                border.width: 1
                                border.color: Theme.accent
                                radius: 20
                            }
                        }
                        
                        // Auto-scan option
                        RowLayout {
                            Layout.topMargin: 16
                            spacing: 12
                            
                            Switch {
                                id: autoScanSwitch
                                checked: backend.getSetting("auto_scan") === "1"
                                onToggled: backend.setSetting("auto_scan", checked ? "1" : "0")
                            }
                            
                            ColumnLayout {
                                spacing: 2
                                
                                Text {
                                    text: "Auto-scan on startup"
                                    font.pixelSize: 14
                                    color: Theme.text
                                }
                                
                                Text {
                                    text: "Automatically scan library when the app starts"
                                    font.pixelSize: 12
                                    color: Theme.textSecondary
                                }
                            }
                        }
                        
                        // Watch for changes option
                        RowLayout {
                            spacing: 12
                            
                            Switch {
                                id: watchChangesSwitch
                                checked: backend.getSetting("watch_changes") === "1"
                                onToggled: backend.setSetting("watch_changes", checked ? "1" : "0")
                            }
                            
                            ColumnLayout {
                                spacing: 2
                                
                                Text {
                                    text: "Watch for file changes"
                                    font.pixelSize: 14
                                    color: Theme.text
                                }
                                
                                Text {
                                    text: "Automatically update when files change"
                                    font.pixelSize: 12
                                    color: Theme.textSecondary
                                }
                            }
                        }
                    }
                }
                
                // FL Studio section
                SettingsSection {
                    title: "FL Studio"
                    
                    ColumnLayout {
                        spacing: 16
                        Layout.fillWidth: true
                        
                        Text {
                            text: "FL Studio Executable Path"
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            color: Theme.text
                        }
                        
                        Text {
                            text: "Set the path to FL Studio for opening FLP files"
                            font.pixelSize: 12
                            color: Theme.textSecondary
                        }
                        
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            
                            Rectangle {
                                Layout.fillWidth: true
                                height: 44
                                radius: 8
                                color: Theme.surfaceHover
                                
                                TextInput {
                                    id: flStudioPathInput
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    font.pixelSize: 13
                                    color: Theme.text
                                    text: backend.getSetting("fl_studio_path")
                                    verticalAlignment: Text.AlignVCenter
                                    
                                    onTextChanged: {
                                        backend.setSetting("fl_studio_path", text)
                                    }
                                }
                            }
                            
                            Button {
                                text: "Browse"
                                onClicked: flStudioDialog.open()
                            }
                        }
                    }
                }
                
                // Performance section
                SettingsSection {
                    title: "Performance"
                    
                    ColumnLayout {
                        spacing: 16
                        Layout.fillWidth: true
                        
                        // Waveform cache size
                        Text {
                            text: "Waveform Cache Size"
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            color: Theme.text
                        }
                        
                        RowLayout {
                            spacing: 16
                            
                            Slider {
                                id: cacheSlider
                                from: 100
                                to: 2000
                                value: parseInt(backend.getSetting("waveform_cache_size_mb")) || 500
                                stepSize: 100
                                Layout.preferredWidth: 200
                                
                                onMoved: {
                                    backend.setSetting("waveform_cache_size_mb", Math.round(value).toString())
                                }
                            }
                            
                            Text {
                                text: Math.round(cacheSlider.value) + " MB"
                                font.pixelSize: 14
                                color: Theme.text
                                Layout.preferredWidth: 80
                            }
                        }
                        
                        // Clear cache button
                        Button {
                            text: "Clear Cache"
                            onClicked: {
                                // Clear waveform cache
                                clearCacheConfirm.open()
                            }
                            
                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 13
                                color: Theme.error
                            }
                            
                            background: Rectangle {
                                color: "transparent"
                                border.width: 1
                                border.color: Theme.error
                                radius: 20
                            }
                        }
                    }
                }
                
                // About section
                SettingsSection {
                    title: "About"
                    
                    ColumnLayout {
                        spacing: 8
                        
                        Text {
                            text: appName
                            font.pixelSize: 18
                            font.weight: Font.Bold
                            color: Theme.text
                        }
                        
                        Text {
                            text: "Version " + appVersion
                            font.pixelSize: 14
                            color: Theme.textSecondary
                        }
                        
                        Text {
                            text: "A Spotify-like library manager for FL Studio projects"
                            font.pixelSize: 14
                            color: Theme.textSecondary
                        }
                        
                        Item { height: 16 }
                        
                        Text {
                            text: "Data stored in: " + backend.getAppDataPath()
                            font.pixelSize: 12
                            color: Theme.textMuted
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: backend.openFolder(backend.getAppDataPath())
                            }
                        }
                    }
                }
                
                Item { Layout.preferredHeight: 32 }
            }
        }
    }
    
    // Settings section component
    component SettingsSection: ColumnLayout {
        property string title: ""
        default property alias content: contentLoader.data
        
        Layout.fillWidth: true
        spacing: 16
        
        Text {
            text: title
            font.pixelSize: 20
            font.weight: Font.Bold
            color: Theme.text
        }
        
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        
        ColumnLayout {
            id: contentLoader
            Layout.fillWidth: true
        }
    }
    
    // Dialogs
    FolderDialog {
        id: folderDialog
        title: "Select Library Folder"
        
        onAccepted: {
            var path = selectedFolder.toString().replace("file:///", "")
            backend.addLibraryRoot(path)
            libraryRootsList.model = backend.getLibraryRoots()
        }
    }
    
    FileDialog {
        id: flStudioDialog
        title: "Select FL Studio Executable"
        nameFilters: ["Executable files (*.exe)"]
        
        onAccepted: {
            var path = selectedFile.toString().replace("file:///", "")
            flStudioPathInput.text = path
        }
    }
    
    Dialog {
        id: clearCacheConfirm
        title: "Clear Cache?"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        anchors.centerIn: parent
        
        contentItem: Text {
            text: "This will delete all cached waveforms.\nThey will be regenerated when needed."
            color: Theme.text
        }
        
        onAccepted: {
            // Clear cache
            // backend.clearWaveformCache()
        }
    }
}
