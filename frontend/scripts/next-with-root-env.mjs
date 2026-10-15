import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { spawn } from 'node:child_process'

const rootEnvPath = resolve(import.meta.dirname, '../../.env')

try {
  for (const line of readFileSync(rootEnvPath, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*(BACKEND_PORT|FRONTEND_PORT|KIRA_API_URL)\s*=\s*(.*?)\s*$/)
    if (!match || process.env[match[1]] !== undefined) continue

    process.env[match[1]] = match[2].replace(/^(?:"|')|(?:"|')$/g, '')
  }
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}

const command = process.argv[2]
if (!['dev', 'build', 'start'].includes(command)) {
  throw new Error('Usage: node scripts/next-with-root-env.mjs <dev|build|start>')
}

const nextArgs = [command]
if (command === 'dev') nextArgs.push('--webpack')
if (command !== 'build') nextArgs.push('-p', process.env.FRONTEND_PORT || '3001')

const child = spawn(process.execPath, ['node_modules/next/dist/bin/next', ...nextArgs], {
  env: process.env,
  stdio: 'inherit',
})

child.on('exit', (code) => process.exit(code ?? 1))
