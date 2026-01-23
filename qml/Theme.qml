pragma Singleton
import QtQuick

QtObject {
    id: theme
    
    // === PREMIUM SKY BLUE & SLATE COLOR PALETTE ===
    
    // Background colors - Deep slate with subtle blue tint
    readonly property color background: "#0c1117"
    readonly property color backgroundLight: "#111820"
    readonly property color backgroundLighter: "#1a2332"
    readonly property color surface: "#151d28"
    readonly property color surfaceHover: "#1e2836"
    readonly property color surfaceActive: "#283344"
    readonly property color surfaceElevated: "#1a2535"
    
    // Primary accent - Sky Blue (Premium feel)
    readonly property color accent: "#38bdf8"
    readonly property color accentHover: "#7dd3fc"
    readonly property color accentDark: "#0ea5e9"
    readonly property color accentMuted: "#0284c7"
    readonly property color accentGlow: "#38bdf830"
    
    // Secondary accent - Soft violet for variety
    readonly property color secondary: "#a78bfa"
    readonly property color secondaryHover: "#c4b5fd"
    
    // Text colors
    readonly property color text: "#f1f5f9"
    readonly property color textSecondary: "#94a3b8"
    readonly property color textMuted: "#64748b"
    readonly property color textDim: "#475569"
    
    // Semantic colors
    readonly property color success: "#34d399"
    readonly property color warning: "#fbbf24"
    readonly property color error: "#f87171"
    readonly property color info: "#60a5fa"
    
    // Gradients
    readonly property color gradientStart: "#38bdf8"
    readonly property color gradientMid: "#818cf8"
    readonly property color gradientEnd: "#a78bfa"
    
    // Glass/Frost effect
    readonly property color glassBg: "#ffffff08"
    readonly property color glassBorder: "#ffffff12"
    
    // Border
    readonly property color border: "#1e293b"
    readonly property color borderLight: "#334155"
    readonly property color borderAccent: "#38bdf840"
    
    // === SIZING ===
    readonly property int radiusXSmall: 4
    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 14
    readonly property int radiusXLarge: 20
    readonly property int radiusRound: 100
    
    // === SPACING ===
    readonly property int spacingXSmall: 4
    readonly property int spacingSmall: 8
    readonly property int spacingMedium: 16
    readonly property int spacingLarge: 24
    readonly property int spacingXLarge: 32
    readonly property int spacingXXLarge: 48
    
    // === ANIMATION DURATIONS ===
    readonly property int animFast: 120
    readonly property int animMedium: 200
    readonly property int animSlow: 300
    readonly property int animSmooth: 400
    
    // === SHADOWS ===
    readonly property string shadowSmall: "0 2px 4px rgba(0,0,0,0.3)"
    readonly property string shadowMedium: "0 4px 12px rgba(0,0,0,0.4)"
    readonly property string shadowLarge: "0 8px 24px rgba(0,0,0,0.5)"
    readonly property string shadowGlow: "0 0 20px rgba(56,189,248,0.3)"
    
    // === FONT SIZES ===
    readonly property int fontXSmall: 10
    readonly property int fontSmall: 12
    readonly property int fontMedium: 14
    readonly property int fontLarge: 16
    readonly property int fontXLarge: 20
    readonly property int fontXXLarge: 28
    readonly property int fontHuge: 36
}
