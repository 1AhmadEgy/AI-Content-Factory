package com.example.core.brand

/** Centralized visual identity for the "افهم واضحك" content brand. */
object BrandConfig {
    const val NAME = "افهم واضحك"
    const val TAGLINE = "وخد المفيد."
    const val INTRO_VOICE = "افهم واضحك… وخد المفيد"

    // Keep these values in one place so UI/render adapters can reuse the same identity.
    const val BACKGROUND_HEX = "#0B1020"
    const val PRIMARY_HEX = "#FFC928"
    const val ACCENT_HEX = "#FF7A3D"
    const val TEXT_HEX = "#FFFFFF"

    const val SHORTS_WIDTH = 1080
    const val SHORTS_HEIGHT = 1920
    const val INTRO_DURATION_MS = 2400L
    const val OUTRO_DURATION_MS = 1800L

    const val WATERMARK_DEFAULT_OPACITY = 0.82f
}
