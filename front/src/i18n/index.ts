import { createI18n } from 'vue-i18n'
import enUS from './locales/en-US'
import frFR from './locales/fr-FR'

const messages = {
  'en-US': enUS,
  'fr-FR': frFR,
}

const locale = localStorage.getItem('userLocale') || navigator.language || 'en-US'
const supportedLocales = Object.keys(messages)
const selectedLocale = supportedLocales.includes(locale) ? locale : 'en-US'

export const i18n = createI18n({
  legacy: false,
  locale: selectedLocale,
  fallbackLocale: 'en-US',
  messages,
})




// Default to browser language or fall back to English
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const getBrowserLocale = (): string => {
  const navigatorLocale = navigator.languages !== undefined
    ? navigator.languages[0]
    : navigator.language

  if (!navigatorLocale) {
    return 'en-US'
  }

  // Check if we have an exact match
  const supportedLocales = Object.keys(messages)
  if (supportedLocales.includes(navigatorLocale)) {
    return navigatorLocale
  }

  // Try to match just the language part (e.g. 'en' from 'en-GB')
  const languageCode = navigatorLocale.split('-')[0]
  for (const locale of supportedLocales) {
    if (locale.startsWith(languageCode)) {
      return locale
    }
  }

  return 'en-US'
}
// Initialize from localStorage if available


