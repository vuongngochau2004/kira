'use client'

import { useServerInsertedHTML } from 'next/navigation'
import { themeScript } from '@/lib/theme-script'

export function ThemeScript() {
  useServerInsertedHTML(() => (
    <script
      id="theme-loader"
      dangerouslySetInnerHTML={{ __html: themeScript }}
    />
  ))
  return null
}
