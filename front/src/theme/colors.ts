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
    primary: '#3b82f6', // Modern blue primary
    'primary-hover': '#2563eb', // Darker blue for hover
    'primary-light': '#dbeafe', // Light blue background
    secondary: '#A3C9A8', // Keep existing accent
    tertiary: '#8b5cf6', // Purple accent
    background: '#fafafa', // Light gray background
    surface: '#ffffff', // White surface
    'surface-secondary': '#f8fafc', // Very light gray
    onPrimary: '#FFFFFF', // White text on primary
    onBackground: '#1e293b', // Dark slate text
    onSurface: '#64748b', // Medium slate text
    border: '#e2e8f0', // Light border
    'border-light': '#f1f5f9', // Lighter border
    error: '#ef4444', // Red error
    success: '#10b981', // Green success
    'success-light': '#d1fae5', // Light green
    warning: '#f59e0b', // Orange warning
    disabled: '#94a3b8', // Muted gray
    focus: '#3b82f6', // Primary for focus
  },
  dark: {
    primary: '#3b82f6',
    'primary-hover': '#2563eb',
    'primary-light': '#1e3a8a',
    secondary: '#ADCBB3',
    tertiary: '#8b5cf6',
    background: '#1F1F1F',
    surface: '#2A2A2A',
    'surface-secondary': '#333333',
    onPrimary: '#FFFFFF',
    onBackground: '#F1F1F1',
    onSurface: '#DDDDDD',
    border: '#444444',
    'border-light': '#3a3a3a',
    error: '#ef4444',
    success: '#10b981',
    'success-light': '#064e3b',
    warning: '#f59e0b',
    disabled: '#666666',
    focus: '#3b82f6',
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

