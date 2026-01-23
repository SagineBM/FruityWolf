import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: projectPage
    
    property var project: null
    property var Theme
    
    signal backClicked()
    signal playTrack(var track)
    
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
                    onClicked: projectPage.backClicked()
                }
            }
            
            ColumnLayout {
                spacing: 4
                
                Text {
                    text: project ? project.project_name : ""
                    font.pixelSize: 28
                    font.weight: Font.Bold
                    color: Theme.text
                }
                
                Text {
                    text: project ? project.project_path : ""
                    font.pixelSize: 12
                    color: Theme.textMuted
                    
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (project) backend.openFolder(project.project_path)
                        }
                    }
                }
            }
            
            Item { Layout.fillWidth: true }
            
            // Action buttons
            Button {
                text: "🎹 Open FLP"
                visible: project && project.flp_path
                onClicked: {
                    if (project) backend.openFlp(project.flp_path)
                }
                
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 13
                    font.weight: Font.Bold
                    color: "#000000"
                }
                
                background: Rectangle {
                    color: parent.hovered ? Theme.accentHover : Theme.accent
                    radius: 20
                }
            }
            
            Button {
                text: "📂 Open Folder"
                onClicked: {
                    if (project) backend.openFolder(project.project_path)
                }
            }
        }
        
        // Tabs
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            
            TabButton {
                text: "Renders (" + (project ? project.renders_count || 1 : 0) + ")"
            }
            TabButton {
                text: "Stems (" + (project ? project.stems_count || 0 : 0) + ")"
                enabled: project && project.stems_dir
            }
            TabButton {
                text: "Samples (" + (project ? project.samples_count || 0 : 0) + ")"
                enabled: project && project.samples_dir
            }
            TabButton {
                text: "Audio (" + (project ? project.audio_count || 0 : 0) + ")"
                enabled: project && project.audio_dir
            }
            TabButton {
                text: "Backup (" + (project ? project.backup_count || 0 : 0) + ")"
                enabled: project && project.backup_dir
            }
        }
        
        // Tab content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex
            
            // Renders
            FileListView {
                model: project ? [project] : []
                emptyText: "No renders found"
                onFileClicked: function(file) {
                    projectPage.playTrack(file)
                }
            }
            
            // Stems
            FileListView {
                model: project && project.stems_dir ? backend.getFilesInFolder(project.stems_dir) : []
                emptyText: "No stems found"
                onFileClicked: function(file) {
                    backend.playTrackDict({
                        title: file.name,
                        path: file.path,
                        project_name: project.project_name
                    })
                }
            }
            
            // Samples
            FileListView {
                model: project && project.samples_dir ? backend.getFilesInFolder(project.samples_dir) : []
                emptyText: "No samples found"
                onFileClicked: function(file) {
                    backend.playTrackDict({
                        title: file.name,
                        path: file.path,
                        project_name: project.project_name
                    })
                }
            }
            
            // Audio
            FileListView {
                model: project && project.audio_dir ? backend.getFilesInFolder(project.audio_dir) : []
                emptyText: "No audio files found"
                onFileClicked: function(file) {
                    backend.playTrackDict({
                        title: file.name,
                        path: file.path,
                        project_name: project.project_name
                    })
                }
            }
            
            // Backup
            BackupListView {
                model: project && project.backup_dir ? backend.getFilesInFolder(project.backup_dir) : []
                emptyText: "No backups found"
            }
        }
    }
    
    component FileListView: ListView {
        property string emptyText: "No files"
        signal fileClicked(var file)
        
        clip: true
        spacing: 2
        
        ScrollBar.vertical: ScrollBar { active: true }
        
        delegate: Rectangle {
            width: parent ? parent.width : 0
            height: 52
            radius: 8
            color: fileMouseArea.containsMouse ? Theme.surfaceHover : "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12
                
                Text {
                    text: "▶"
                    font.pixelSize: 14
                    color: Theme.accent
                }
                
                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    
                    Text {
                        text: modelData.name || modelData.title || "Unknown"
                        font.pixelSize: 14
                        color: Theme.text
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    
                    Text {
                        text: modelData.size_formatted || ""
                        font.pixelSize: 12
                        color: Theme.textMuted
                    }
                }
            }
            
            MouseArea {
                id: fileMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: fileClicked(modelData)
            }
        }
        
        Text {
            anchors.centerIn: parent
            visible: parent.count === 0
            text: emptyText
            font.pixelSize: 14
            color: Theme.textMuted
        }
    }
    
    component BackupListView: ListView {
        property string emptyText: "No backups"
        
        clip: true
        spacing: 2
        
        delegate: Rectangle {
            width: parent ? parent.width : 0
            height: 48
            radius: 8
            color: backupMouseArea.containsMouse ? Theme.surfaceHover : "transparent"
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12
                
                Text {
                    text: "📄"
                    font.pixelSize: 16
                }
                
                Text {
                    text: modelData.name || "Unknown"
                    font.pixelSize: 14
                    color: Theme.text
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                
                Text {
                    text: modelData.size_formatted || ""
                    font.pixelSize: 12
                    color: Theme.textMuted
                }
            }
            
            MouseArea {
                id: backupMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    backend.openFlp(modelData.path)
                }
            }
        }
        
        Text {
            anchors.centerIn: parent
            visible: parent.count === 0
            text: emptyText
            font.pixelSize: 14
            color: Theme.textMuted
        }
    }
}
