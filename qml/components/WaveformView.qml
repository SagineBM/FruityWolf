import QtQuick
import QtQuick.Controls

// Reusable Waveform Canvas
Item {
    id: root
    
    // Properties
    property var peaksMin: []
    property var peaksMax: []
    property real position: 0  // 0-1 playback position
    property color waveformColor: Theme.accentMuted
    property color playedColor: Theme.accent
    property color centerColor: Theme.background
    property real barWidth: 2
    property real gap: 1
    
    // Signals
    signal seek(real pos)
    
    onPeaksMinChanged: canvas.requestPaint()
    onPeaksMaxChanged: canvas.requestPaint()
    onPositionChanged: canvas.requestPaint()
    
    function setPeaks(min, max) {
        peaksMin = min
        peaksMax = max
    }
    
    Canvas {
        id: canvas
        anchors.fill: parent
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Threaded
        
        onPaint: {
            var ctx = getContext("2d")
            var w = width
            var h = height
            var cy = h / 2
            
            ctx.clearRect(0, 0, w, h)
            
            // Draw center line
            // ctx.strokeStyle = "#334155"
            // ctx.lineWidth = 1
            // ctx.beginPath()
            // ctx.moveTo(0, cy)
            // ctx.lineTo(w, cy)
            // ctx.stroke()
            
            if (!peaksMin || peaksMin.length === 0) {
                // Draw placeholder line
                ctx.strokeStyle = Theme.border
                ctx.lineWidth = 1
                ctx.beginPath()
                ctx.moveTo(0, cy)
                ctx.lineTo(w, cy)
                ctx.stroke()
                return
            }
            
            var count = peaksMin.length
            var barW = w / count
            
            // Playhead x position
            var playX = position * w
            
            for (var i = 0; i < count; i++) {
                var x = i * barW
                
                // Color based on playhead
                if (x < playX) {
                    ctx.fillStyle = playedColor
                } else {
                    ctx.fillStyle = waveformColor
                }
                
                // Height scaling (peaks are usually -1 to 1?)
                // Assuming peaks are normalized -1 to 1 or similar
                // But backend sends raw values or normalized? 
                // Let's assume normalized -1 to 1 for now or check backend.
                // Actually backend extracts min/max.
                
                var min = peaksMin[i]
                var max = peaksMax[i]
                
                // Normalize amplitude if needed. 
                // Assuming backend sends float values. 
                // If they are small, we scale them. 
                // Let's assume they are somewhat normalized 
                // or we compute max amplitude here. 
                // For performance, better if backend normalizes.
                // Assuming standard -1 to 1 range for audio.
                
                var hTop = Math.abs(max) * (h/2)
                var hBot = Math.abs(min) * (h/2)
                
                // Draw bar
                // ctx.fillRect(x, cy - hTop, barW, hTop + hBot)
                // Actually lets draw clearer bars
                
                var topY = cy - hTop
                var heightBar = hTop + hBot
                
                // Clamping
                if (heightBar < 1) heightBar = 1
                
                // Gap
                if (barW > 2) {
                     ctx.fillRect(x, topY, barW - gap, heightBar)
                } else {
                     ctx.fillRect(x, topY, barW, heightBar)
                }
            }
        }
    }
    
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        
        onClicked: (mouse) => {
            var pos = mouse.x / width
            root.seek(pos)
        }
        
        onPositionChanged: (mouse) => {
            if (pressed) {
                var pos = Math.max(0, Math.min(1, mouse.x / width))
                root.seek(pos)
            }
        }
    }
}
