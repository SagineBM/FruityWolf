import QtQuick
import QtQuick.Effects
import ".."

// Premium Icon Button with hover effects and optional highlight state
Rectangle {
    id: root
    
    property string iconPath: ""
    property int iconSize: 20
    property int buttonSize: 40
    property bool highlighted: false
    property bool enabled: true
    property string tooltip: ""
    property color iconColor: highlighted ? Theme.accent : Theme.textSecondary
    property color hoverColor: Theme.surfaceHover
    
    signal clicked()
    
    width: buttonSize
    height: buttonSize
    radius: buttonSize / 2
    color: mouseArea.containsMouse && enabled ? hoverColor : "transparent"
    opacity: enabled ? 1 : 0.4
    
    Behavior on color {
        ColorAnimation { duration: Theme.animFast }
    }
    
    Behavior on opacity {
        NumberAnimation { duration: Theme.animFast }
    }
    
    // Icon
    SvgIcon {
        anchors.centerIn: parent
        pathData: root.iconPath
        size: root.iconSize
        color: mouseArea.containsMouse && enabled ? Theme.text : root.iconColor
        
        Behavior on color {
            ColorAnimation { duration: Theme.animFast }
        }
        
        // Subtle scale animation on hover
        scale: mouseArea.containsMouse && enabled ? 1.08 : 1
        Behavior on scale {
            NumberAnimation { duration: Theme.animFast; easing.type: Easing.OutBack }
        }
    }
    
    // Glow effect when highlighted
    Rectangle {
        visible: root.highlighted
        anchors.centerIn: parent
        width: parent.width + 4
        height: parent.height + 4
        radius: width / 2
        color: "transparent"
        border.width: 2
        border.color: Theme.accentGlow
        opacity: 0.5
        
        SequentialAnimation on opacity {
            running: root.highlighted
            loops: Animation.Infinite
            NumberAnimation { to: 0.8; duration: 1000; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.3; duration: 1000; easing.type: Easing.InOutSine }
        }
    }
    
    // Tooltip
    ToolTip {
        visible: mouseArea.containsMouse && root.tooltip
        text: root.tooltip
        delay: 500
    }
    
    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        
        onClicked: {
            if (root.enabled) {
                root.clicked()
            }
        }
    }
    
    // Tooltip component
    component ToolTip: Rectangle {
        property string text: ""
        property int delay: 500
        
        x: (parent.width - width) / 2
        y: parent.height + 8
        width: tooltipText.implicitWidth + 16
        height: tooltipText.implicitHeight + 8
        radius: Theme.radiusSmall
        color: Theme.surfaceElevated
        border.width: 1
        border.color: Theme.border
        z: 1000
        
        Text {
            id: tooltipText
            anchors.centerIn: parent
            text: parent.text
            font.pixelSize: Theme.fontSmall
            color: Theme.textSecondary
        }
    }
}
