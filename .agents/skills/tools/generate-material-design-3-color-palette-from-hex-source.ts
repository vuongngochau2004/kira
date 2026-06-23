#!/usr/bin/env bun
/**
 * Generate Material Design 3 Color Palette from a base hex color
 *
 * Uses @material/material-color-utilities to generate proper MD3 palettes
 *
 * Usage:
 *   bun generate-material-design-3-color-palette-from-hex-source.ts "#006E2D"
 *   bun generate-material-design-3-color-palette-from-hex-source.ts "#006E2D" --json
 */

import { applyTheme, argbFromHex, themeFromSourceColor } from '@material/material-color-utilities'

interface MD3ColorSet {
  primary: string
  onPrimary: string
  primaryContainer: string
  onPrimaryContainer: string
  secondary: string
  onSecondary: string
  secondaryContainer: string
  onSecondaryContainer: string
  tertiary: string
  onTertiary: string
  tertiaryContainer: string
  onTertiaryContainer: string
  error: string
  onError: string
  errorContainer: string
  onErrorContainer: string
  background: string
  onBackground: string
  surface: string
  onSurface: string
  surfaceVariant: string
  onSurfaceVariant: string
  outline: string
  outlineVariant: string
  shadow: string
  scrim: string
  inverseSurface: string
  inverseOnSurface: string
  inversePrimary: string
}

// Helper: ARGB int to Hex
function argbToHex(argb: number): string {
  const r = (argb >> 16) & 0xff
  const g = (argb >> 8) & 0xff
  const b = argb & 0xff
  return (
    '#' +
    [r, g, b]
      .map((x) => x.toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase()
  )
}

// Generate MD3 palette from source color
function generateMD3Palette(sourceHex: string): MD3ColorSet {
  const argb = argbFromHex(sourceHex)
  const theme = themeFromSourceColor(argb)

  const s = theme.schemes.light
  const e = theme.schemes.light // Error colors

  return {
    primary: argbToHex(s.primary),
    onPrimary: argbToHex(s.onPrimary),
    primaryContainer: argbToHex(s.primaryContainer),
    onPrimaryContainer: argbToHex(s.onPrimaryContainer),
    secondary: argbToHex(s.secondary),
    onSecondary: argbToHex(s.onSecondary),
    secondaryContainer: argbToHex(s.secondaryContainer),
    onSecondaryContainer: argbToHex(s.onSecondaryContainer),
    tertiary: argbToHex(s.tertiary),
    onTertiary: argbToHex(s.onTertiary),
    tertiaryContainer: argbToHex(s.tertiaryContainer),
    onTertiaryContainer: argbToHex(s.onTertiaryContainer),
    error: argbToHex(s.error),
    onError: argbToHex(s.onError),
    errorContainer: argbToHex(s.errorContainer),
    onErrorContainer: argbToHex(s.onErrorContainer),
    background: argbToHex(s.background),
    onBackground: argbToHex(s.onBackground),
    surface: argbToHex(s.surface),
    onSurface: argbToHex(s.onSurface),
    surfaceVariant: argbToHex(s.surfaceVariant),
    onSurfaceVariant: argbToHex(s.onSurfaceVariant),
    outline: argbToHex(s.outline),
    outlineVariant: argbToHex(s.outlineVariant),
    shadow: argbToHex(s.shadow),
    scrim: argbToHex(s.scrim),
    inverseSurface: argbToHex(s.inverseSurface),
    inverseOnSurface: argbToHex(s.inverseOnSurface),
    inversePrimary: argbToHex(s.inversePrimary),
  }
}

// CLI interface
const args = process.argv.slice(2)

if (args.length === 0) {
  console.error(
    'Usage: bun generate-material-design-3-color-palette-from-hex-source.ts <hex-color> [--json]',
  )
  process.exit(1)
}

const baseColor = args[0].replace('#', '').toUpperCase()
const fullHex = '#' + baseColor.padStart(6, '0')

try {
  const palette = generateMD3Palette(fullHex)

  if (args.includes('--json')) {
    console.log(JSON.stringify(palette, null, 2))
  } else {
    console.log('\n🎨 Material Design 3 Palette')
    console.log(`Source: ${fullHex}\n`)
    console.log(JSON.stringify(palette, null, 2))
  }
} catch (e) {
  console.error('Error generating palette:', e)
  process.exit(1)
}

export { generateMD3Palette, type MD3ColorSet }
