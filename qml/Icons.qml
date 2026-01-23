pragma Singleton
import QtQuick

QtObject {
    // Navigation Icons (SVG Path Data - Lucide-inspired)
    readonly property string home: "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10"
    readonly property string library: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M4 4.5A2.5 2.5 0 0 0 6.5 7H20V4H6.5a2.5 2.5 0 0 0 0 5H20v11a2 2 0 0 1-2 2H6.5"
    readonly property string heart: "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
    readonly property string heartFilled: "M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
    readonly property string listMusic: "M21 15V6 M18.5 18a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z M3 8h10 M3 12h7 M3 16h4"
    readonly property string settings: "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
    readonly property string folder: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
    readonly property string folderOpen: "M6 14L4 5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6"
    readonly property string plus: "M12 5v14 M5 12h14"
    readonly property string search: "M11 17.25a6.25 6.25 0 1 1 0-12.5 6.25 6.25 0 0 1 0 12.5z M16 16l4.5 4.5"
    readonly property string x: "M18 6L6 18 M6 6l12 12"
    readonly property string refresh: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8 M21 3v5h-5 M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16 M3 21v-5h5"
    
    // Player Icons
    readonly property string play: "M5 3l14 9-14 9z"
    readonly property string pause: "M6 4h4v16H6z M14 4h4v16h-4z"
    readonly property string skipBack: "M19 20L9 12l10-8z M5 4v16"
    readonly property string skipForward: "M5 4l10 8-10 8z M19 4v16"
    readonly property string shuffle: "M16 3h5v5 M21 3l-8.5 8.5 M21 16v5h-5 M21 21l-8.5-8.5 M4 4l16 16"
    readonly property string repeat: "M17 1l4 4-4 4 M3 11V9a4 4 0 0 1 4-4h14 M7 23l-4-4 4-4 M21 13v2a4 4 0 0 1-4 4H3"
    readonly property string repeatOne: "M17 1l4 4-4 4 M3 11V9a4 4 0 0 1 4-4h14 M7 23l-4-4 4-4 M21 13v2a4 4 0 0 1-4 4H3 M12 10v6 M11 10h2"
    readonly property string volumeHigh: "M11 5L6 9H2v6h4l5 4z M15.5 8.5a5 5 0 0 1 0 7 M19 5a9 9 0 0 1 0 14"
    readonly property string volumeLow: "M11 5L6 9H2v6h4l5 4z M15.5 8.5a5 5 0 0 1 0 7"
    readonly property string volumeMute: "M11 5L6 9H2v6h4l5 4z M22 9l-6 6 M16 9l6 6"
    
    // Action Icons
    readonly property string music: "M9 18V5l12-2v13 M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"
    readonly property string piano: "M3 5h18v14H3z M7 5v8 M11 5v8 M15 5v8 M19 5v8"
    readonly property string waveform: "M12 3v18 M4 8v8 M8 6v12 M16 6v12 M20 8v8"
    readonly property string sparkles: "M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z M19 16l1 3 3 1-3 1-1 3-1-3-3-1 3-1z M5 19l.5 1.5L7 21l-1.5.5L5 23l-.5-1.5L3 21l1.5-.5z"
    readonly property string barChart: "M12 20V10 M18 20V4 M6 20v-4"
    readonly property string externalLink: "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6 M15 3h6v6 M10 14L21 3"
    readonly property string info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 16v-4 M12 8h.01"
    readonly property string clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 6v6l3 3"
    readonly property string chevronLeft: "M15 18l-6-6 6-6"
    readonly property string chevronRight: "M9 18l6-6-6-6"
    readonly property string chevronDown: "M6 9l6 6 6-6"
    readonly property string menu: "M3 12h18 M3 6h18 M3 18h18"
    readonly property string sidebar: "M3 3h18v18H3z M9 3v18"
    readonly property string keyboard: "M2 6h20v12H2z M6 10h.01 M10 10h.01 M14 10h.01 M18 10h.01 M8 14h8"
    readonly property string command: "M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"
}
