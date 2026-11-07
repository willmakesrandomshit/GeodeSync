"""GeodeSync Phoenix Design System & Unified Color Palette.

A professional, focused, modern dark theme adhering to strict visual hierarchy:
- Primary Accent: Neon Cyan (#00F0FF) / Emerald (#10B981)
- Surfaces: Deep obsidian (#0B0E14) to neutral slate cards (#131822)
- High contrast, accessible typography and zero rainbow borders.
"""

THEME = {
    # Core Surfaces
    "background": "#0B0E14",
    "surface": "#121722",
    "surface_elevated": "#181F2E",
    "surface_highlight": "#1E273A",
    "panel": "#121722",
    "panel_alt": "#181F2E",
    "card": "#131822",
    
    # Borders & Dividers
    "border": "#202838",
    "border_subtle": "#161D2A",
    "border_focus": "#00F0FF",
    
    # Typography
    "text": "#F8FAFC",          # High contrast main text
    "text_secondary": "#94A3B8",# Muted body text
    "muted": "#94A3B8",         # Backward compatible key
    "text_quiet": "#64748B",    # Subtitle / caption
    "quiet": "#64748B",         # Backward compatible key
    
    # Restrained Accents
    "primary": "#00F0FF",       # Neon Cyan / Main Action Accent
    "primary_hover": "#38F5FF",
    "accent": "#00F0FF",
    "accent_hover": "#38F5FF",
    "accent_dark": "#0A2833",
    
    # Semantic Indicators
    "success": "#10B981",       # Emerald green
    "success_dark": "#062E21",
    "lime": "#10B981",          # Backward compatible key
    "lime_dark": "#062E21",
    
    # Warnings
    "warning": "#F59E0B",       # Warm amber
    "warning_dark": "#3B2605",
    "amber": "#F59E0B",         # Backward compatible key
    "amber_dark": "#3B2605",
    
    # Destructive / Errors
    "danger": "#EF4444",        # Soft red
    "danger_dark": "#381014",
    "red": "#EF4444",           # Backward compatible key
    "red_dark": "#381014",
    
    # Auxiliary Accents (retained for backward compatibility with existing tests)
    "cyan": "#00F0FF",
    "cyan_dark": "#0A2833",
    "lilac": "#8B5CF6",
    "lilac_dark": "#251745",
}

# Typography presets
FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "subtitle": ("Segoe UI", 12, "bold"),
    "heading": ("Segoe UI", 10, "bold"),
    "body": ("Segoe UI", 9),
    "body_bold": ("Segoe UI", 9, "bold"),
    "caption": ("Segoe UI", 8),
    "caption_bold": ("Segoe UI", 8, "bold"),
    "code": ("Consolas", 9),
}
