import { ComputedRef } from 'vue';

export interface I18n {
  t: (key: string, params?: Record<string, unknown>) => string;
  setLocale: (locale: string) => void;
  currentLocale: ComputedRef<string>;
  availableLocales: string[];
}

export const i18n: I18n;
export function setLocale(locale: string): void;
export function t(key: string, params?: Record<string, unknown>): string;

export default i18n;