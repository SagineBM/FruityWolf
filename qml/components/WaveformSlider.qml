import QtQuick
import QtQuick.Controls

// Slider replacement with Waveform background
Item {
    id: root
    
    property real value: 0  // 0-1
    property real buffer: 0 // Download progress if needed
    property var peaksMin: []
    property var peaksMax: []
    
    signal moved(real val)
    
    height: 40
    
    WaveformView {
        id: waveform
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        
        peaksMin: root.peaksMin
        peaksMax: root.peaksMax
        position: root.value
        
        // Mini style
        waveformColor: Theme.surfaceHover
        playedColor: Theme.accent
        barWidth: 3
        gap: 1
        
        onSeek: (pos) => {
            root.moved(pos)
        }
    }
    
    // Hover effect line?
    // Playhead line?
    Rectangle {
        x: root.value * root.width
        width: 2
        height: parent.height
        color: Theme.text
        visible: root.peaksMin && root.peaksMin.length > 0
    }
}
