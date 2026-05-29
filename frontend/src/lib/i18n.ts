import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en'
import vi from './locales/vi'

export const resources = {
  en: { translation: en },
  vi: { translation: vi },
} as const

export type TranslationKeys = typeof en
export type LanguageCode = 'en' | 'vi'

export type Language = {
  code: LanguageCode
  label: string
  nativeLabel: string
}

export const languages: Language[] = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'vi', label: 'Vietnamese', nativeLabel: 'Tiếng Việt' },
]

export const LANGUAGE_STORAGE_KEY = 'kira-language'

if (!i18n.isInitialized) {
  i18n
    .use(initReactI18next)
    .init({
      resources,
      lng: 'vi', // Hardcoded to prevent SSR/client hydration mismatch
      fallbackLng: 'vi',
      supportedLngs: ['en', 'vi'],
      interpolation: {
        escapeValue: false,
      },
    })
}

export default i18n