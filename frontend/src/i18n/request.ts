import { getRequestConfig } from 'next-intl/server'
import { cookies, headers } from 'next/headers'

export const locales = ['en', 'vi'] as const
export type Locale = (typeof locales)[number]
export const defaultLocale: Locale = 'en'

export const languages: { code: Locale; label: string; nativeLabel: string }[] = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'vi', label: 'Vietnamese', nativeLabel: 'Tiếng Việt' },
]

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const headersList = await headers()

  let locale: Locale = defaultLocale

  // 1. Check cookie first (user preference)
  const cookieLocale = cookieStore.get('NEXT_LOCALE')?.value as Locale | undefined
  if (cookieLocale && locales.includes(cookieLocale)) {
    locale = cookieLocale
  }

  // 2. Fall back to Accept-Language header
  if (!cookieLocale) {
    const acceptLanguage = headersList.get('accept-language')
    if (acceptLanguage) {
      const preferred = acceptLanguage.split(',')[0].split('-')[0]
      if (locales.includes(preferred as Locale)) {
        locale = preferred as Locale
      }
    }
  }

  return {
    locale,
    messages: (await import(`../locales/${locale}/index.ts`)).default,
  }
})
