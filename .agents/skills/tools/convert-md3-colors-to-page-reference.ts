#!/usr/bin/env bun
/**
 * Convert MD3 color palettes to page-color-palettes.json format
 * With balanced hue distribution
 */

import { readFileSync } from 'fs'

interface SourceItem {
  seed: string
  scheme12: {
    primary: string
    onPrimary: string
    primaryContainer: string
    onPrimaryContainer: string
    background: string
    onBackground: string
    surface: string
    onSurface: string
    surfaceVariant: string
    onSurfaceVariant: string
    outline: string
    error: string
  }
}

interface ColorPalette {
  slug_name: string
  display_name: string
  mood_keywords: string[]
  best_for: string[]
  base_color: string
  set: {
    primary: string
    onPrimary: string
    primaryContainer: string
    onPrimaryContainer: string
    background: string
    onBackground: string
    surface: string
    onSurface: string
    surfaceVariant: string
    onSurfaceVariant: string
    outline: string
    error: string
  }
}

// Color psychology mapping with more granular hue ranges
function analyzeColor(hex: string): {
  name: string
  mood: string[]
  bestFor: string[]
  hue: number
  category: string
} {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)

  // Convert to HSL
  const max = Math.max(r, g, b) / 255
  const min = Math.min(r, g, b) / 255
  const l = (max + min) / 2

  let h = 0
  if (max !== min) {
    const d = max - min
    h =
      max === r / 255
        ? 60 * (((g / 255 - b / 255) / d) % 6)
        : max === g / 255
          ? 60 * ((b / 255 - r / 255) / d + 2)
          : 60 * ((r / 255 - g / 255) / d + 4)
  }
  if (h < 0) h += 360

  // Color categorization by hue - more granular
  if (h < 10) {
    return {
      name: 'Crimson Red',
      mood: ['intense', 'passionate', 'bold', 'urgent'],
      bestFor: ['sales', 'ecommerce', 'food', 'cta'],
      hue: h,
      category: 'red',
    }
  } else if (h < 25) {
    return {
      name: 'Vivid Red',
      mood: ['energetic', 'bold', 'passionate', 'attention-grabbing'],
      bestFor: ['sales', 'ecommerce', 'entertainment', 'food'],
      hue: h,
      category: 'red',
    }
  } else if (h < 40) {
    return {
      name: 'Warm Orange',
      mood: ['friendly', 'enthusiastic', 'warm', 'playful'],
      bestFor: ['b2c', 'food', 'youth', 'lifestyle'],
      hue: h,
      category: 'orange',
    }
  } else if (h < 50) {
    return {
      name: 'Golden Amber',
      mood: ['warm', 'energetic', 'friendly', 'optimistic'],
      bestFor: ['food', 'lifestyle', 'youth', 'creative'],
      hue: h,
      category: 'orange',
    }
  } else if (h < 60) {
    return {
      name: 'Sunny Yellow',
      mood: ['optimistic', 'cheerful', 'attention-grabbing', 'warm'],
      bestFor: ['b2c', 'youth', 'creative', 'lifestyle'],
      hue: h,
      category: 'yellow',
    }
  } else if (h < 75) {
    return {
      name: 'Fresh Lime',
      mood: ['fresh', 'energetic', 'vibrant', 'youthful'],
      bestFor: ['b2c', 'healthcare', 'food', 'creative'],
      hue: h,
      category: 'lime',
    }
  } else if (h < 90) {
    return {
      name: 'Spring Green',
      mood: ['fresh', 'renewing', 'optimistic', 'natural'],
      bestFor: ['healthcare', 'wellness', 'education', 'saas'],
      hue: h,
      category: 'green',
    }
  } else if (h < 105) {
    return {
      name: 'Emerald Green',
      mood: ['fresh', 'nature', 'growth', 'professional'],
      bestFor: ['saas', 'b2b', 'healthcare', 'finance'],
      hue: h,
      category: 'green',
    }
  } else if (h < 120) {
    return {
      name: 'Forest Green',
      mood: ['natural', 'grounded', 'trustworthy', 'calm'],
      bestFor: ['outdoor', 'environmental', 'wellness', 'education'],
      hue: h,
      category: 'green',
    }
  } else if (h < 140) {
    return {
      name: 'Teal Green',
      mood: ['calm', 'balanced', 'trustworthy', 'healing'],
      bestFor: ['healthcare', 'wellness', 'education', 'saas'],
      hue: h,
      category: 'teal',
    }
  } else if (h < 160) {
    return {
      name: 'Ocean Teal',
      mood: ['calm', 'professional', 'modern', 'clean'],
      bestFor: ['saas', 'b2b', 'healthcare', 'technology'],
      hue: h,
      category: 'teal',
    }
  } else if (h < 180) {
    return {
      name: 'Aquamarine',
      mood: ['refreshing', 'calm', 'clean', 'serene'],
      bestFor: ['wellness', 'spa', 'healthcare', 'lifestyle'],
      hue: h,
      category: 'cyan',
    }
  } else if (h < 200) {
    return {
      name: 'Sky Cyan',
      mood: ['fresh', 'clean', 'modern', 'light'],
      bestFor: ['technology', 'saas', 'cleaning', 'healthcare'],
      hue: h,
      category: 'cyan',
    }
  } else if (h < 220) {
    return {
      name: 'Sky Blue',
      mood: ['calm', 'trustworthy', 'professional', 'serene'],
      bestFor: ['saas', 'b2b', 'healthcare', 'technology'],
      hue: h,
      category: 'blue',
    }
  } else if (h < 240) {
    return {
      name: 'Azure Blue',
      mood: ['professional', 'trustworthy', 'corporate', 'secure'],
      bestFor: ['b2b', 'finance', 'enterprise', 'technology'],
      hue: h,
      category: 'blue',
    }
  } else if (h < 255) {
    return {
      name: 'Royal Blue',
      mood: ['professional', 'authoritative', 'trustworthy', 'classic'],
      bestFor: ['b2b', 'finance', 'enterprise', 'corporate'],
      hue: h,
      category: 'blue',
    }
  } else if (h < 275) {
    return {
      name: 'Indigo',
      mood: ['wise', 'intuitive', 'deep', 'professional'],
      bestFor: ['technology', 'b2b', 'education', 'consulting'],
      hue: h,
      category: 'indigo',
    }
  } else if (h < 290) {
    return {
      name: 'Royal Purple',
      mood: ['luxury', 'creative', 'mysterious', 'premium'],
      bestFor: ['b2c', 'beauty', 'creative', 'premium'],
      hue: h,
      category: 'purple',
    }
  } else if (h < 310) {
    return {
      name: 'Vibrant Magenta',
      mood: ['playful', 'energetic', 'bold', 'youthful'],
      bestFor: ['b2c', 'beauty', 'fashion', 'creative'],
      hue: h,
      category: 'magenta',
    }
  } else if (h < 330) {
    return {
      name: 'Fuchsia Pink',
      mood: ['bold', 'feminine', 'energetic', 'trendy'],
      bestFor: ['fashion', 'beauty', 'youth', 'creative'],
      hue: h,
      category: 'pink',
    }
  } else if (h < 345) {
    return {
      name: 'Soft Pink',
      mood: ['gentle', 'feminine', 'warm', 'caring'],
      bestFor: ['beauty', 'healthcare', 'wellness', 'fashion'],
      hue: h,
      category: 'pink',
    }
  } else {
    return {
      name: 'Rose Red',
      mood: ['romantic', 'gentle', 'warm', 'elegant'],
      bestFor: ['beauty', 'fashion', 'wellness', 'lifestyle'],
      hue: h,
      category: 'red',
    }
  }
}

// Generate slug from name
function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

// Main conversion
const sourcePath = '/Users/user/Workplace/projects/tools/m3_material/page-color.json'
const sourceContent = JSON.parse(readFileSync(sourcePath, 'utf-8'))

const totalItems = sourceContent.items.length // 1080
const targetCount = 40 // Aim for 40 diverse colors

// Sample at strategic intervals across the hue wheel
// Source has 120 hue steps with 9 items each (3 chromas x 3 tones)
const sampleIndices: number[] = []

// Sample across the entire array to hit different hue regions
// 1080 items / 40 target ≈ 27 items per sample
// But we want to sample within each hue group
for (let i = 0; i < totalItems; i += 27) {
  // Add the base index
  sampleIndices.push(i)
  // Add offset to get different chroma/tone combinations
  if (i + 5 < totalItems) sampleIndices.push(i + 5)
  if (i + 10 < totalItems) sampleIndices.push(i + 10)
}

const palettes: ColorPalette[] = []
const seenSeeds = new Set<string>()
const hueBuckets: Record<number, ColorPalette[]> = {}

// Target: 2-3 colors per 30-degree hue bucket (360/30 = 12 buckets)
const maxPerBucket = 3

for (const idx of sampleIndices) {
  if (idx >= totalItems) break
  if (palettes.length >= targetCount) break

  const item: SourceItem = sourceContent.items[idx]

  // Skip duplicate seeds
  if (seenSeeds.has(item.seed)) continue
  seenSeeds.add(item.seed)

  const analysis = analyzeColor(item.seed)
  const bucket = Math.floor(analysis.hue / 30)

  // Check bucket count
  if (!hueBuckets[bucket]) hueBuckets[bucket] = []
  if (hueBuckets[bucket].length >= maxPerBucket) continue

  palettes.push({
    slug_name: slugify(analysis.name) + '-' + item.seed.slice(1).toLowerCase(),
    display_name: analysis.name,
    mood_keywords: analysis.mood,
    best_for: analysis.bestFor,
    base_color: item.seed,
    set: {
      primary: item.scheme12.primary,
      onPrimary: item.scheme12.onPrimary,
      primaryContainer: item.scheme12.primaryContainer,
      onPrimaryContainer: item.scheme12.onPrimaryContainer,
      background: item.scheme12.background,
      onBackground: item.scheme12.onBackground,
      surface: item.scheme12.surface,
      onSurface: item.scheme12.onSurface,
      surfaceVariant: item.scheme12.surfaceVariant,
      onSurfaceVariant: item.scheme12.onSurfaceVariant,
      outline: item.scheme12.outline,
      error: item.scheme12.error,
    },
  })

  hueBuckets[bucket].push(palettes[palettes.length - 1])
}

// Sort by hue for visual consistency
palettes.sort((a, b) => {
  const hueA = analyzeColor(a.base_color).hue
  const hueB = analyzeColor(b.base_color).hue
  return hueA - hueB
})

// Output
console.log(JSON.stringify(palettes, null, 2))
