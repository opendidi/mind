/**
 * useTheme — Dark/light mode toggle with localStorage persistence.
 */
import { ref, watchEffect } from 'vue'

const THEME_KEY = 'mind-theme'
const isDark = ref(false)

// Restore saved preference on load
function loadTheme() {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'dark') {
    isDark.value = true
  } else if (saved === 'light') {
    isDark.value = false
  } else {
    // No preference → follow system
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
}

function applyTheme(dark: boolean) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
}

// Apply on mount and when isDark changes
loadTheme()
applyTheme(isDark.value)

watchEffect(() => {
  applyTheme(isDark.value)
})

export function useTheme() {
  return { isDark, toggleTheme }
}
