import QtQuick
import QtQuick.Shapes

// Reusable SVG Icon Component - renders path data as vector graphics
Item {
    id: root
    
    property string pathData: ""
    property color color: Theme.textSecondary
    property int size: 24
    property real strokeWidth: 2
    property bool filled: false
    
    width: size
    height: size
    
    Shape {
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
                path: root.pathData
            }
        }
    }
}
