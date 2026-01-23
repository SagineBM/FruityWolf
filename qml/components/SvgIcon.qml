import QtQuick
import QtQuick.Shapes
import ".."

// Reusable SVG Icon Component - renders from icon folder or path data
Item {
    id: root
    
    property string iconName: ""      // Filename from Icons.qml (e.g., Icons.play)
    property string pathData: ""      // Raw SVG path data (fallback)
    property color color: Theme.textSecondary
    property int size: 24
    property real strokeWidth: 2
    property bool filled: false
    
    width: size
    height: size
    
    // Determine the source URL
    readonly property string resolvedSource: {
        if (iconName === "") return ""
        // If it starts with a path data character (M, L), it's probably path data
        if (iconName.startsWith("M") || iconName.startsWith("L")) return ""
        return Icons.iconBase + iconName
    }

    // Image for file-based icons
    Image {
        id: iconImage
        visible: root.resolvedSource !== ""
        anchors.fill: parent
        source: root.resolvedSource
        sourceSize: Qt.size(root.size, root.size)
        smooth: true
        fillMode: Image.PreserveAspectFit
        
        // Note: Tinting in QML usually requires ColorOverlay or MultiEffect.
        // We assume the environment supports basic layer effects.
    }
    
    // Shape for path data (fallback and backward compatibility)
    Shape {
        visible: root.resolvedSource === "" && (root.pathData !== "" || root.iconName !== "")
        anchors.fill: parent
        
        ShapePath {
            strokeColor: root.filled ? "transparent" : root.color
            strokeWidth: root.strokeWidth
            fillColor: root.filled ? root.color : "transparent"
            strokeJoinStyle: ShapePath.RoundJoin
            strokeCapStyle: ShapePath.RoundCap
            
            // Scale path to fit size (paths are 24x24 by default)
            scale: Qt.size(root.size / 24, root.size / 24)
            
            PathSvg {
                path: root.pathData !== "" ? root.pathData : root.iconName
            }
        }
    }
}
