/** @type {import('tailwindcss').Config} */
const { colors } = require('./src/theme/colors')

module.exports = {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  media: false,
  darkMode: 'class', // or 'media' based on your preference
  theme: {
    extend: {
      colors: {
        // Map theme colors to Tailwind utility classes
        primary: colors.light.primary,
        'primary-light': colors.dark.primary, // Lighter variant for hover states
        secondary: colors.light.secondary,
        tertiary: colors.light.tertiary,
        background: colors.light.background,
        surface: colors.light.surface,
        onPrimary: colors.light.onPrimary,
        onBackground: colors.light.onBackground,
        onSurface: colors.light.onSurface,
        border: colors.light.border,
        error: colors.light.error,
        success: colors.light.success,
        disabled: colors.light.disabled,
        focus: colors.light.focus,
        // Ajout du warning pour conformité UI
        warning: '#FFD882', // Jaune pastel (voir charte)
        'warning-light': '#FFEBA6', // Variante claire (mode dark ou hover)
        onWarning: '#3A3A3A', // Texte sur fond warning (contraste élevé)
      },
    },
  },
  plugins: [],
}
