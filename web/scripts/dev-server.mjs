import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'

import { buildNextArgs, finalizeDevServerOptions, resolveDevServerOptions } from './dev-server-lib.mjs'

const require = createRequire(import.meta.url)

async function main() {
  const baseOptions = resolveDevServerOptions(process.argv.slice(2), process.env)
  const options = await finalizeDevServerOptions(baseOptions)
  const nextBin = require.resolve('next/dist/bin/next')

  if (options.fallbackMessage) {
    console.warn(`[dev-server] ${options.fallbackMessage}`)
  }

  const displayHost = options.host === '0.0.0.0' ? 'localhost' : options.host
  console.log(`[dev-server] Starting Next ${options.mode} on http://${displayHost}:${options.port}`)

  const env = {
    ...process.env,
    NODE_OPTIONS: `${process.env.NODE_OPTIONS || ''} --max-old-space-size=4096`.trim(),
  }

  let isShuttingDown = false
  let currentChild = null

  const forwardSignal = (signal) => {
    isShuttingDown = true
    if (currentChild && !currentChild.killed) {
      currentChild.kill(signal)
    }
  }

  process.on('SIGINT', forwardSignal)
  process.on('SIGTERM', forwardSignal)

  while (!isShuttingDown) {
    const exitCode = await new Promise((resolve) => {
      const child = spawn(process.execPath, [nextBin, ...buildNextArgs(options)], {
        stdio: ['ignore', 'inherit', 'inherit'],
        env,
      })
      currentChild = child

      child.on('error', (err) => {
        console.error('[dev-server] Child error:', err)
      })

      child.on('exit', (code, signal) => {
        currentChild = null
        if (code !== 0 && code !== null) {
          console.error(`[dev-server] Child process exited with code: ${code}, signal: ${signal}`)
        }
        resolve(code ?? (signal ? 1 : 0))
      })
    })

    if (isShuttingDown) {
      process.exit(exitCode)
    }

    console.warn('[dev-server] Dev server stopped unexpectedly. Auto-restarting in 2s...')
    await new Promise((r) => setTimeout(r, 2000))
  }
}

main().catch((error) => {
  console.error('[dev-server] Failed to start Next.js', error)
  process.exit(1)
})
