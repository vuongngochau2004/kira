#!/usr/bin/env bun
/**
 * Convert MD3 color palettes to page-color-palettes.json format
 * With color_name_keywords for text matching
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
  color_name_keywords: string[]
  hue_range: [number, number]
  saturation: string
  brightness: string
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

// Color name mappings (EN + VI)
const colorNames: Record<string, { en: string[]; vi: string[]; category: string }> = {
  crimson_red: {
    en: ['red', 'crimson', 'ruby', 'scarlet'],
    vi: ['đỏ', 'đỏ tươi', 'hồng đỏ'],
    category: 'red',
  },
  vivid_red: {
    en: ['red', 'vivid', 'bright red'],
    vi: ['đỏ', 'đỏ tươi', 'đỏ sáng'],
    category: 'red',
  },
  warm_orange: {
    en: ['orange', 'warm orange', 'amber'],
    vi: ['cam', 'màu cam', 'vàng cam'],
    category: 'orange',
  },
  golden_amber: {
    en: ['amber', 'gold', 'golden'],
    vi: ['hổ phách', 'vàng', 'vàng gold'],
    category: 'orange',
  },
  sunny_yellow: {
    en: ['yellow', 'sunny', 'lemon'],
    vi: ['vàng', 'vàng tươi', 'vàng chanh'],
    category: 'yellow',
  },
  fresh_lime: {
    en: ['lime', 'green lime', 'fresh green'],
    vi: ['xanh chanh', 'xanh lá tươi', 'xanh non'],
    category: 'lime',
  },
  spring_green: {
    en: ['green', 'spring green', 'light green'],
    vi: ['xanh lá', 'xanh lá non', 'xanh nhạt'],
    category: 'green',
  },
  emerald_green: {
    en: ['green', 'emerald', 'forest green'],
    vi: ['xanh lá', 'xanh lá cây', 'xanh rừng'],
    category: 'green',
  },
  forest_green: {
    en: ['green', 'forest', 'dark green'],
    vi: ['xanh rừng', 'xanh lá đậm', 'xanh thẫm'],
    category: 'green',
  },
  teal_green: {
    en: ['teal', 'green teal', 'dark teal'],
    vi: ['xanh ngọc bích', 'xanh lục bảo đậm'],
    category: 'teal',
  },
  ocean_teal: {
    en: ['teal', 'ocean', 'sea green'],
    vi: ['xanh biển', 'xanh lục bảo', 'xanh ngọc'],
    category: 'teal',
  },
  aquamarine: {
    en: ['cyan', 'aquamarine', 'turquoise'],
    vi: ['xanh lơ', 'xanh ngọc nhạt', 'xanh thủy tinh'],
    category: 'cyan',
  },
  sky_cyan: {
    en: ['cyan', 'sky cyan', 'light blue'],
    vi: ['xanh lơ', 'xanh da trời', 'xanh nhạt'],
    category: 'cyan',
  },
  sky_blue: {
    en: ['blue', 'sky blue', 'light blue'],
    vi: ['xanh', 'xanh da trời', 'xanh nhạt'],
    category: 'blue',
  },
  azure_blue: {
    en: ['blue', 'azure', 'corporate blue'],
    vi: ['xanh', 'xanh dương', 'xanh doanh nghiệp'],
    category: 'blue',
  },
  royal_blue: {
    en: ['blue', 'royal blue', 'navy'],
    vi: ['xanh', 'xanh hoàng gia', 'xanh đậm'],
    category: 'blue',
  },
  indigo: {
    en: ['indigo', 'purple blue', 'deep blue'],
    vi: ['xanh tím', 'xanh chàm', 'xanh thẫm'],
    category: 'indigo',
  },
  royal_purple: {
    en: ['purple', 'royal purple', 'violet'],
    vi: ['tím', 'tím hoàng gia', 'tím sáng'],
    category: 'purple',
  },
  vibrant_magenta: {
    en: ['magenta', 'pink', 'hot pink'],
    vi: ['hồng sẫm', 'magenta', 'hồng đậm'],
    category: 'magenta',
  },
  fuchsia_pink: {
    en: ['pink', 'fuchsia', 'hot pink'],
    vi: ['hồng', 'hồng sẫm', 'hồng tươi'],
    category: 'pink',
  },
  soft_pink: {
    en: ['pink', 'soft pink', 'rose'],
    vi: ['hồng', 'hồng nhạt', 'hồng phấn'],
    category: 'pink',
  },
  rose_red: {
    en: ['red', 'rose', 'pink red'],
    vi: ['đỏ hồng', 'hồng đỏ', 'đỏ nhạt'],
    category: 'red',
  },
}

// Hue ranges for each category
const hueRanges: Record<string, [number, number]> = {
  red: [345, 15],
  orange: [15, 45],
  yellow: [45, 70],
  lime: [70, 85],
  green: [85, 145],
  teal: [145, 175],
  cyan: [175, 195],
  blue: [195, 255],
  indigo: [255, 275],
  purple: [275, 310],
  magenta: [310, 330],
  pink: [330, 345],
}

function analyzeColor(hex: string): {
  name: string
  mood: string[]
  bestFor: string[]
  hue: number
  category: string
  saturation: string
  brightness: string
} {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)

  const max = Math.max(r, g, b) / 255
  const min = Math.min(r, g, b) / 255

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

  // Determine saturation
  const s = max === 0 ? 0 : (max - min) / (1 - Math.abs(2 * 0.5 - max)) // Using 0.5 as mid brightness
  const saturation = s < 0.3 ? 'low' : s < 0.6 ? 'medium' : 'high'

  // Determine brightness
  const l = (max + min) / 2
  const brightness = l < 0.4 ? 'dark' : l > 0.6 ? 'light' : 'medium'

  // Color categorization
  if (h < 15 || h >= 345) {
    return {
      name: h < 10 ? 'Crimson Red' : 'Rose Red',
      mood: ['intense', 'passionate', 'bold'],
      bestFor: ['sales', 'ecommerce', 'food'],
      hue: h,
      category: 'red',
      saturation,
      brightness,
    }
  } else if (h < 25) {
    return {
      name: 'Vivid Red',
      mood: ['energetic', 'bold', 'passionate'],
      bestFor: ['sales', 'ecommerce', 'entertainment'],
      hue: h,
      category: 'red',
      saturation,
      brightness,
    }
  } else if (h < 40) {
    return {
      name: 'Warm Orange',
      mood: ['friendly', 'enthusiastic', 'warm'],
      bestFor: ['b2c', 'food', 'youth'],
      hue: h,
      category: 'orange',
      saturation,
      brightness,
    }
  } else if (h < 50) {
    return {
      name: 'Golden Amber',
      mood: ['warm', 'energetic', 'optimistic'],
      bestFor: ['food', 'lifestyle', 'youth'],
      hue: h,
      category: 'orange',
      saturation,
      brightness,
    }
  } else if (h < 60) {
    return {
      name: 'Sunny Yellow',
      mood: ['optimistic', 'cheerful', 'attention-grabbing'],
      bestFor: ['b2c', 'youth', 'creative'],
      hue: h,
      category: 'yellow',
      saturation,
      brightness,
    }
  } else if (h < 75) {
    return {
      name: 'Fresh Lime',
      mood: ['fresh', 'energetic', 'vibrant'],
      bestFor: ['b2c', 'healthcare', 'creative'],
      hue: h,
      category: 'lime',
      saturation,
      brightness,
    }
  } else if (h < 90) {
    return {
      name: 'Spring Green',
      mood: ['fresh', 'renewing', 'optimistic'],
      bestFor: ['healthcare', 'wellness', 'education'],
      hue: h,
      category: 'green',
      saturation,
      brightness,
    }
  } else if (h < 105) {
    return {
      name: 'Emerald Green',
      mood: ['fresh', 'nature', 'growth', 'professional'],
      bestFor: ['saas', 'b2b', 'healthcare', 'finance'],
      hue: h,
      category: 'green',
      saturation,
      brightness,
    }
  } else if (h < 120) {
    return {
      name: 'Forest Green',
      mood: ['natural', 'grounded', 'trustworthy'],
      bestFor: ['outdoor', 'environmental', 'wellness'],
      hue: h,
      category: 'green',
      saturation,
      brightness,
    }
  } else if (h < 140) {
    return {
      name: 'Teal Green',
      mood: ['calm', 'balanced', 'trustworthy'],
      bestFor: ['healthcare', 'wellness', 'education'],
      hue: h,
      category: 'teal',
      saturation,
      brightness,
    }
  } else if (h < 160) {
    return {
      name: 'Ocean Teal',
      mood: ['calm', 'professional', 'modern'],
      bestFor: ['saas', 'b2b', 'healthcare'],
      hue: h,
      category: 'teal',
      saturation,
      brightness,
    }
  } else if (h < 180) {
    return {
      name: 'Aquamarine',
      mood: ['refreshing', 'calm', 'clean'],
      bestFor: ['wellness', 'spa', 'healthcare'],
      hue: h,
      category: 'cyan',
      saturation,
      brightness,
    }
  } else if (h < 200) {
    return {
      name: 'Sky Cyan',
      mood: ['fresh', 'clean', 'modern'],
      bestFor: ['technology', 'saas', 'cleaning'],
      hue: h,
      category: 'cyan',
      saturation,
      brightness,
    }
  } else if (h < 220) {
    return {
      name: 'Sky Blue',
      mood: ['calm', 'trustworthy', 'professional'],
      bestFor: ['saas', 'b2b', 'healthcare'],
      hue: h,
      category: 'blue',
      saturation,
      brightness,
    }
  } else if (h < 240) {
    return {
      name: 'Azure Blue',
      mood: ['professional', 'trustworthy', 'corporate'],
      bestFor: ['b2b', 'finance', 'enterprise'],
      hue: h,
      category: 'blue',
      saturation,
      brightness,
    }
  } else if (h < 255) {
    return {
      name: 'Royal Blue',
      mood: ['professional', 'authoritative', 'trustworthy'],
      bestFor: ['b2b', 'finance', 'enterprise'],
      hue: h,
      category: 'blue',
      saturation,
      brightness,
    }
  } else if (h < 275) {
    return {
      name: 'Indigo',
      mood: ['wise', 'intuitive', 'deep'],
      bestFor: ['technology', 'b2b', 'education'],
      hue: h,
      category: 'indigo',
      saturation,
      brightness,
    }
  } else if (h < 290) {
    return {
      name: 'Royal Purple',
      mood: ['luxury', 'creative', 'mysterious'],
      bestFor: ['b2c', 'beauty', 'premium'],
      hue: h,
      category: 'purple',
      saturation,
      brightness,
    }
  } else if (h < 310) {
    return {
      name: 'Vibrant Magenta',
      mood: ['playful', 'energetic', 'bold'],
      bestFor: ['b2c', 'beauty', 'fashion'],
      hue: h,
      category: 'magenta',
      saturation,
      brightness,
    }
  } else if (h < 330) {
    return {
      name: 'Fuchsia Pink',
      mood: ['bold', 'feminine', 'energetic'],
      bestFor: ['fashion', 'beauty', 'youth'],
      hue: h,
      category: 'pink',
      saturation,
      brightness,
    }
  } else {
    return {
      name: 'Soft Pink',
      mood: ['gentle', 'feminine', 'warm'],
      bestFor: ['beauty', 'healthcare', 'wellness'],
      hue: h,
      category: 'pink',
      saturation,
      brightness,
    }
  }
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

// Main conversion
const sourcePath = '/Users/user/Workplace/projects/tools/m3_material/page-color.json'
const sourceContent = JSON.parse(readFileSync(sourcePath, 'utf-8'))

const totalItems = sourceContent.items.length
const targetCount = 40

const sampleIndices: number[] = []
for (let i = 0; i < totalItems; i += 27) {
  sampleIndices.push(i)
  if (i + 5 < totalItems) sampleIndices.push(i + 5)
  if (i + 10 < totalItems) sampleIndices.push(i + 10)
}

const palettes: ColorPalette[] = []
const seenSeeds = new Set<string>()
const hueBuckets: Record<number, ColorPalette[]> = {}
const maxPerBucket = 3

for (const idx of sampleIndices) {
  if (idx >= totalItems) break
  if (palettes.length >= targetCount) break

  const item: SourceItem = sourceContent.items[idx]
  if (seenSeeds.has(item.seed)) continue
  seenSeeds.add(item.seed)

  const analysis = analyzeColor(item.seed)
  const bucket = Math.floor(analysis.hue / 30)

  if (!hueBuckets[bucket]) hueBuckets[bucket] = []
  if (hueBuckets[bucket].length >= maxPerBucket) continue

  // Get color name keywords
  const colorKey = slugify(analysis.name).replace(/-/g, '_')
  const colorNameData = colorNames[colorKey] || {
    en: [analysis.category],
    vi: [],
    category: analysis.category,
  }

  palettes.push({
    slug_name: slugify(analysis.name) + '-' + item.seed.slice(1).toLowerCase(),
    display_name: analysis.name,
    color_name_keywords: [...colorNameData.en, ...colorNameData.vi],
    hue_range: hueRanges[analysis.category] || [analysis.hue - 15, analysis.hue + 15],
    saturation: analysis.saturation,
    brightness: analysis.brightness,
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

// Sort by hue
palettes.sort((a, b) => {
  const hueA = analyzeColor(a.base_color).hue
  const hueB = analyzeColor(b.base_color).hue
  return hueA - hueB
})

console.log(JSON.stringify(palettes, null, 2))
