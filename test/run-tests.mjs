import { readdir } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import console from 'node:console'
import os from 'node:os'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath, URL } from 'node:url'

const root = path.resolve(fileURLToPath(new URL('..', import.meta.url)))
const testDir = path.join(root, 'test')
const entries = await readdir(testDir)
const testFiles = entries
  .filter(name => name.endsWith('.test.ts'))
  .sort()
  .map(name => path.join(testDir, name))

if (testFiles.length === 0) {
  console.error('No test files found in test/*.test.ts')
  process.exit(1)
}

const child = spawn(
  process.execPath,
  ['--import', 'tsx', '--test', ...testFiles],
  {
    stdio: 'inherit',
    env: {
      ...process.env,
      TCM_AGENT_HOME: path.join(os.tmpdir(), `tcm-agent-tests-${process.pid}`),
    },
  },
)

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }

  process.exit(code ?? 1)
})
