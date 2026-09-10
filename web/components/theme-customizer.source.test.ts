import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

describe('theme customizer source', () => {
  it('offers light, dark, and system modes from personalization', () => {
    const src = fs.readFileSync(path.resolve(__dirname, 'theme-customizer.tsx'), 'utf8')

    expect(src).toContain("setTheme('light')")
    expect(src).toContain("setTheme('dark')")
    expect(src).toContain("setTheme('system')")
    expect(src).toContain("t('modeToggle.system')")
  })
})
