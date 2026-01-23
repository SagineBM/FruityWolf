pragma Singleton
import QtQuick

QtObject {
    // Base path for icons - assumes QML is in qml/ and icons are in FruityWolf/resources/icons/
    readonly property string iconBase: "../FruityWolf/resources/icons/"

    // Navigation Icons
    readonly property string home: "music-library-2-svgrepo-com.svg"
    readonly property string library: "checklist-minimalistic-svgrepo-com.svg"
    readonly property string heart: "red-heart-svgrepo-com.svg"
    readonly property string listMusic: "plaaylist-minimalistic-svgrepo-com.svg"
    readonly property string settings: "settings-svgrepo-com.svg"
    readonly property string folder: "folder-2-svgrepo-com.svg"
    readonly property string folderOpen: "folder-open-svgrepo-com.svg"
    readonly property string plus: "add-circle-svgrepo-com.svg"
    readonly property string search: "search-svgrepo-com.svg"
    readonly property string x: "close-square-svgrepo-com.svg"
    readonly property string refresh: "restart-svgrepo-com.svg"
    
    // Player Icons
    readonly property string play: "play-circle-svgrepo-com.svg"
    readonly property string pause: "pause-circle-svgrepo-com.svg"
    readonly property string skipBack: "skip-previous-svgrepo-com.svg"
    readonly property string skipForward: "skip-next-svgrepo-com.svg"
    readonly property string shuffle: "restart-svgrepo-com.svg" // Reuse restart for now
    readonly property string repeat: "repeat-svgrepo-com.svg"
    readonly property string repeatOne: "repeat-one-svgrepo-com.svg"
    readonly property string volumeHigh: "volume-svgrepo-com.svg"
    readonly property string volumeMute: "volume-cross-svgrepo-com.svg"
    
    // Action Icons
    readonly property string music: "music-note-3-svgrepo-com.svg"
    readonly property string waveform: "soundwave-svgrepo-com.svg"
    readonly property string info: "alert-circle-svgrepo-com.svg"
    readonly property string clock: "time-clock-circle-svgrepo-com.svg"
    readonly property string edit: "pen-edit-square-svgrepo-com.svg"
    readonly property string trash: "trash-bin-trash-svgrepo-com.svg"
    readonly property string check: "verified-check-svgrepo-com.svg"
    readonly property string flStudio: "fl-studio-mobile-svgrepo-com.svg"
    readonly property string tag: "tag-svgrepo-com.svg"
}}
