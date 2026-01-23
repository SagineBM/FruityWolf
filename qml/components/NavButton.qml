import QtQuick
import QtQuick.Layouts
import ".."

// Navigation Button with icon and text - premium styling
Rectangle {
    id: root
    
    property string iconPath: ""
    property string text: ""
    property bool selected: false
    property string shortcut: ""
    
    signal clicked()
    
    Layout.fillWidth: true
    height: 44
    radius: Theme.radiusMedium
    
    // Gradient background for selected state
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { 
            position: 0.0
            color: root.selected ? Theme.accentGlow : (mouseArea.containsMouse ? Theme.surfaceHover : "transparent")
        }
        GradientStop { 
            position: 1.0
            color: root.selected ? "transparent" : (mouseArea.containsMouse ? Theme.surfaceHover : "transparent")
        }
    }
    
    Behavior on opacity {
        NumberAnimation { duration: Theme.animFast }
    }
    
    // Left accent bar for selected state
    Rectangle {
        visible: root.selected
        width: 3
        height: 20
        radius: 2
        anchors.left: parent.left
        anchors.leftMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.accent
        
        Behavior on opacity {
            NumberAnimation { duration: Theme.animMedium }
        }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingMedium
        anchors.rightMargin: Theme.spacingMedium
        spacing: Theme.spacingMedium
        
        // Icon
        SvgIcon {
            pathData: root.iconPath
            size: 20
            color: root.selected ? Theme.accent : (mouseArea.containsMouse ? Theme.text : Theme.textSecondary)
            
            Behavior on color {
                ColorAnimation { duration: Theme.animFast }
            }
        }
        
        // Text
        Text {
            Layout.fillWidth: true
            text: root.text
            font.pixelSize: Theme.fontMedium
            font.weight: root.selected ? Font.DemiBold : Font.Medium
            color: root.selected ? Theme.text : (mouseArea.containsMouse ? Theme.text : Theme.textSecondary)
            elide: Text.ElideRight
            
            Behavior on color {
                ColorAnimation { duration: Theme.animFast }
            }
        }
        
        // Keyboard shortcut hint
        Text {
            visible: root.shortcut && mouseArea.containsMouse
            text: root.shortcut
            font.pixelSize: Theme.fontXSmall
            font.family: "monospace"
            color: Theme.textMuted
            opacity: 0.7
            
            Behavior on opacity {
                NumberAnimation { duration: Theme.animFast }
            }
        }
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
