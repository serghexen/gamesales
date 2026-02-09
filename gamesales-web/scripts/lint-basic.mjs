import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, extname } from 'node:path'

const ROOT = new URL('../src', import.meta.url)
const EXTENSIONS = new Set(['.js', '.vue'])
const IGNORE_DIRS = new Set(['node_modules', 'dist'])

const errors = []

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    if (IGNORE_DIRS.has(entry)) continue
    const full = join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      walk(full)
      continue
    }
    if (!EXTENSIONS.has(extname(full))) continue
    lintFile(full)
  }
}

function lintFile(filePath) {
  const content = readFileSync(filePath, 'utf8')
  const lines = content.split('\n')

  lines.forEach((line, idx) => {
    const n = idx + 1
    if (/\s+$/.test(line)) {
      errors.push(`${filePath}:${n} trailing spaces`)
    }
    if (/\t/.test(line)) {
      errors.push(`${filePath}:${n} tab character found`) 
    }
    if (/\bdebugger\b/.test(line)) {
      errors.push(`${filePath}:${n} debugger statement`) 
    }
    // Разрешаем console в специальных утилитах/скриптах, но в src обычно это шум.
    if (/\bconsole\.(log|debug|info)\(/.test(line)) {
      errors.push(`${filePath}:${n} console.* call`) 
    }
  })

  if (!content.endsWith('\n')) {
    errors.push(`${filePath}: missing final newline`)
  }
}

walk(ROOT.pathname)

if (errors.length) {
  console.error('Basic lint failed:')
  for (const err of errors) console.error(`- ${err}`)
  process.exit(1)
}

console.log('Basic lint passed')
