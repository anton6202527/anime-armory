import './load-env.ts'

import { loadBackendConfig, SERVICE_NAME } from './config.ts'
import { createBackendServer } from './server.ts'

const config = loadBackendConfig()
const server = createBackendServer({ config })

server.listen(config.port, config.host, () => {
  process.stdout.write(`${SERVICE_NAME} listening on http://${config.host}:${config.port}\n`)
})

const shutdown = (signal: NodeJS.Signals): void => {
  process.stdout.write(`${SERVICE_NAME} received ${signal}; shutting down\n`)
  server.close((error) => {
    if (error) {
      process.stderr.write(`${SERVICE_NAME} shutdown failed\n`)
      process.exitCode = 1
    }
  })
}

process.once('SIGINT', shutdown)
process.once('SIGTERM', shutdown)
