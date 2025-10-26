/**
 * Application Color Theme
 *
 * This file centralizes color definitions used throughout the application.
 * Use these variables instead of hardcoded Tailwind classes to maintain consistency.
 */

/**
 * Application Color Theme (Light/Dark)
 *
 * Palette centralisée pour cohérence UI.
 * Utiliser colors[mode][role] pour obtenir la couleur selon le mode.
 */

export type ThemeMode = 'light' | 'dark';

export const colors = {
  light: {
    primary: '#F27B70', // Action principale
    secondary: '#A3C9A8', // Accent secondaire
    tertiary: '#FFD882', // Mise en valeur douce
    background: '#FDF8EF', // Fond principal
    surface: '#FFFFFF', // Fond des composants
    onPrimary: '#FFFFFF', // Texte sur boutons primaires
    onBackground: '#3A3A3A', // Texte principal
    onSurface: '#444444', // Texte secondaire
    border: '#DADADA', // Séparateurs
    error: '#D9605E', // Alertes critiques
    success: '#77C29B', // Messages positifs
    disabled: '#CCCCCC', // Inactifs
    focus: '#82A6D2', // Focus clavier/hover
  },
  dark: {
    primary: '#F58C82',
    secondary: '#ADCBB3',
    tertiary: '#FFEBA6',
    background: '#1F1F1F',
    surface: '#2A2A2A',
    onPrimary: '#1F1F1F',
    onBackground: '#F1F1F1',
    onSurface: '#DDDDDD',
    border: '#444444',
    error: '#F58C8A',
    success: '#93D1B1',
    disabled: '#666666',
    focus: '#A1C0F2',
  },
} as const;

/**
 * Helper pour obtenir la couleur selon le mode.
 * @param key Nom du rôle
 * @param mode 'light' ou 'dark'
 */
export function getColor(key: keyof typeof colors.light, mode: ThemeMode = 'light') {
  return colors[mode][key];
}

