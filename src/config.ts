import { mkdir, readFile, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { isEnoentError } from './utils/errors.js'

export type TcmAgentSettings = {
  env?: Record<string, string | number>
  model?: string
  maxOutputTokens?: number
  // NOTE: temperature 控制模型输出的随机性。
  // 中医辨证场景应使用低值（0.1-0.3），确保证型/方剂输出结构稳定；
  // 开放问答场景可适当调高（0.7-1.0）。
  temperature?: number
  mcpServers?: Record<string, McpServerConfig>
}

export type McpServerConfig = {
  command: string
  args?: string[]
  env?: Record<string, string | number>
  url?: string
  headers?: Record<string, string | number>
  cwd?: string
  enabled?: boolean
  protocol?: 'auto' | 'content-length' | 'newline-json' | 'streamable-http'
}

export type RuntimeConfig = {
  model: string
  baseUrl: string
  authToken?: string
  apiKey?: string
  maxOutputTokens?: number
  // NOTE: 未设置时由适配器使用 provider 默认值（通常为 1.0）。
  // TCM-Agent 在辨证推理场景中应显式设置为 0.2，以保证输出的结构一致性。
  temperature?: number
  mcpServers: Record<string, McpServerConfig>
  sourceSummary: string
}

export type McpConfigScope = 'user' | 'project'

export const TCM_AGENT_DIR = process.env.TCM_AGENT_HOME
  ? path.resolve(process.env.TCM_AGENT_HOME)
  : path.join(os.homedir(), '.tcm-agent')
export const TCM_AGENT_SETTINGS_PATH = path.join(TCM_AGENT_DIR, 'settings.json')
export const TCM_AGENT_HISTORY_PATH = path.join(TCM_AGENT_DIR, 'history.jsonl')
export const TCM_AGENT_PERMISSIONS_PATH = path.join(TCM_AGENT_DIR, 'permissions.json')
export const TCM_AGENT_MCP_PATH = path.join(TCM_AGENT_DIR, 'mcp.json')
export const TCM_AGENT_MCP_TOKENS_PATH = path.join(TCM_AGENT_DIR, 'mcp-tokens.json')
export const TCM_AGENT_PROJECTS_DIR = path.join(TCM_AGENT_DIR, 'projects')
export const CLAUDE_SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json')
export const PROJECT_MCP_PATH = path.join(process.cwd(), '.mcp.json')

export async function readMcpTokensFile(
  filePath = TCM_AGENT_MCP_TOKENS_PATH,
): Promise<Record<string, string>> {
  try {
    const content = await readFile(filePath, 'utf8')
    const parsed = JSON.parse(content) as unknown
    if (typeof parsed !== 'object' || parsed === null) {
      return {}
    }
    return parsed as Record<string, string>
  } catch (error) {
    if (isEnoentError(error)) return {}
    throw error
  }
}

export async function saveMcpTokensFile(
  tokens: Record<string, string>,
  filePath = TCM_AGENT_MCP_TOKENS_PATH,
): Promise<void> {
  await mkdir(path.dirname(filePath), { recursive: true })
  await writeFile(filePath, `${JSON.stringify(tokens, null, 2)}\n`, 'utf8')
}

async function readSettingsFile(filePath: string): Promise<TcmAgentSettings> {
  try {
    const content = await readFile(filePath, 'utf8')
    return JSON.parse(content) as TcmAgentSettings
  } catch (error) {
    if (isEnoentError(error)) {
      return {}
    }

    throw error
  }
}

export async function readMcpConfigFile(
  filePath: string,
): Promise<Record<string, McpServerConfig>> {
  try {
    const content = await readFile(filePath, 'utf8')
    const parsed = JSON.parse(content) as unknown
    if (
      typeof parsed !== 'object' ||
      parsed === null ||
      !('mcpServers' in parsed) ||
      typeof parsed.mcpServers !== 'object' ||
      parsed.mcpServers === null
    ) {
      return {}
    }

    return parsed.mcpServers as Record<string, McpServerConfig>
  } catch (error) {
    if (isEnoentError(error)) {
      return {}
    }

    throw error
  }
}

export function getMcpConfigPath(
  scope: McpConfigScope,
  cwd = process.cwd(),
): string {
  return scope === 'project' ? path.join(cwd, '.mcp.json') : TCM_AGENT_MCP_PATH
}

export async function loadScopedMcpServers(
  scope: McpConfigScope,
  cwd = process.cwd(),
): Promise<Record<string, McpServerConfig>> {
  return readMcpConfigFile(getMcpConfigPath(scope, cwd))
}

export async function saveScopedMcpServers(
  scope: McpConfigScope,
  servers: Record<string, McpServerConfig>,
  cwd = process.cwd(),
): Promise<void> {
  const targetPath = getMcpConfigPath(scope, cwd)
  await mkdir(path.dirname(targetPath), { recursive: true })
  await writeFile(
    targetPath,
    `${JSON.stringify({ mcpServers: servers }, null, 2)}\n`,
    'utf8',
  )
}

function mergeSettings(
  base: TcmAgentSettings,
  override: TcmAgentSettings,
): TcmAgentSettings {
  const mergedMcpServers = {
    ...(base.mcpServers ?? {}),
  }

  for (const [name, server] of Object.entries(override.mcpServers ?? {})) {
    mergedMcpServers[name] = {
      ...(mergedMcpServers[name] ?? {}),
      ...server,
      env: {
        ...(mergedMcpServers[name]?.env ?? {}),
        ...(server.env ?? {}),
      },
      headers: {
        ...(mergedMcpServers[name]?.headers ?? {}),
        ...(server.headers ?? {}),
      },
    }
  }

  return {
    ...base,
    ...override,
    env: {
      ...(base.env ?? {}),
      ...(override.env ?? {}),
    },
    mcpServers: mergedMcpServers,
  }
}

export async function loadEffectiveSettings(): Promise<TcmAgentSettings> {
  const [claudeSettings, globalMcpConfig, projectMcpConfig, tcmAgentSettings] =
    await Promise.all([
      readSettingsFile(CLAUDE_SETTINGS_PATH),
      readMcpConfigFile(TCM_AGENT_MCP_PATH),
      readMcpConfigFile(PROJECT_MCP_PATH),
      readSettingsFile(TCM_AGENT_SETTINGS_PATH),
    ])
  return mergeSettings(
    mergeSettings(
      mergeSettings(claudeSettings, { mcpServers: globalMcpConfig }),
      { mcpServers: projectMcpConfig },
    ),
    tcmAgentSettings,
  )
}

export async function saveTcmAgentSettings(
  updates: TcmAgentSettings,
): Promise<void> {
  await mkdir(TCM_AGENT_DIR, { recursive: true })
  const existing = await readSettingsFile(TCM_AGENT_SETTINGS_PATH)
  const next = mergeSettings(existing, updates)
  await writeFile(
    TCM_AGENT_SETTINGS_PATH,
    `${JSON.stringify(next, null, 2)}\n`,
    'utf8',
  )
}

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const effectiveSettings = await loadEffectiveSettings()
  const env = {
    ...(effectiveSettings.env ?? {}),
    ...process.env,
  }

  const model =
    process.env.TCM_AGENT_MODEL ||
    effectiveSettings.model ||
    String(env.ANTHROPIC_MODEL ?? '').trim()

  const baseUrl =
    String(env.ANTHROPIC_BASE_URL ?? '').trim() || 'https://api.anthropic.com'
  const authToken = String(env.ANTHROPIC_AUTH_TOKEN ?? '').trim() || undefined
  const apiKey = String(env.ANTHROPIC_API_KEY ?? '').trim() || undefined
  const rawMaxOutputTokens =
    process.env.TCM_AGENT_MAX_OUTPUT_TOKENS ??
    effectiveSettings.maxOutputTokens ??
    env.TCM_AGENT_MAX_OUTPUT_TOKENS
  const parsedMaxOutputTokens =
    rawMaxOutputTokens === undefined ? NaN : Number(rawMaxOutputTokens)
  const maxOutputTokens =
    Number.isFinite(parsedMaxOutputTokens) && parsedMaxOutputTokens > 0
      ? Math.floor(parsedMaxOutputTokens)
      : undefined

  // NOTE: temperature 读取优先级：环境变量 TCM_TEMPERATURE / TCM_AGENT_TEMPERATURE > settings.json
  // TCM-Agent 辨证场景建议设置为 0.2，开放问答场景可不设置（使用 provider 默认值）。
  const rawTemperature =
    process.env.TCM_TEMPERATURE ??
    process.env.TCM_AGENT_TEMPERATURE ??
    effectiveSettings.temperature
  const parsedTemperature =
    rawTemperature === undefined ? NaN : Number(rawTemperature)
  const temperature =
    Number.isFinite(parsedTemperature) && parsedTemperature >= 0 && parsedTemperature <= 2
      ? parsedTemperature
      : undefined

  if (!model) {
    throw new Error(
      `No model configured. Set ~/.tcm-agent/settings.json or env.ANTHROPIC_MODEL.`,
    )
  }

  if (!authToken && !apiKey) {
    throw new Error(
      `No auth configured. Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY in ~/.tcm-agent/settings.json or process env.`,
    )
  }

  return {
    model,
    baseUrl,
    authToken,
    apiKey,
    maxOutputTokens,
    temperature,
    mcpServers: effectiveSettings.mcpServers ?? {},
    sourceSummary: `config: ${TCM_AGENT_SETTINGS_PATH} > ${CLAUDE_SETTINGS_PATH} > process.env`,
  }
}
