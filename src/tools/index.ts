import type { McpServerConfig, RuntimeConfig } from '../config.js'
import type { McpServerSummary } from '../mcp.js'
import { createMcpBackedTools } from '../mcp.js'
import { discoverSkills } from '../skills.js'
import { ToolRegistry } from '../tool.js'
import { askUserTool } from './ask-user.js'
import { editFileTool } from './edit-file.js'
import { grepFilesTool } from './grep-files.js'
import { listFilesTool } from './list-files.js'
import { createLoadSkillTool } from './load-skill.js'
import { modifyFileTool } from './modify-file.js'
import { patchFileTool } from './patch-file.js'
import { readFileTool } from './read-file.js'
import { runCommandTool } from './run-command.js'
import { webFetchTool } from './web-fetch.js'
import { webSearchTool } from './web-search.js'
import { writeFileTool } from './write-file.js'
import type { ToolProfile } from '../tool-profile.js'
import { TCM_CONSULTATION_MCP_SERVERS } from '../tool-profile.js'

function summarizeServerEndpoint(config: McpServerConfig): string {
  const remoteUrl = config.url?.trim()
  if (remoteUrl) return remoteUrl
  const command = config.command?.trim() ?? ''
  const args = config.args?.join(' ') ?? ''
  return `${command} ${args}`.trim()
}

function buildConnectingMcpSummaries(
  mcpServers: Record<string, McpServerConfig>,
): McpServerSummary[] {
  return Object.entries(mcpServers).map(([name, config]) => ({
    name,
    command: summarizeServerEndpoint(config),
    status: config.enabled === false ? 'disabled' : 'connecting',
    toolCount: 0,
    protocol:
      config.protocol === 'auto' || config.protocol === undefined
        ? undefined
        : config.protocol,
  }))
}

export async function createDefaultToolRegistry(args: {
  cwd: string
  runtime: RuntimeConfig | null
  profile?: ToolProfile
}): Promise<ToolRegistry> {
  const profile = args.profile ?? 'coding'
  const skills = await discoverSkills(args.cwd)
  const mcpServers = args.runtime?.mcpServers ?? {}
  const localTools = profile === 'tcm-consultation'
    ? [askUserTool]
    : [
        askUserTool,
        listFilesTool,
        grepFilesTool,
        readFileTool,
        writeFileTool,
        modifyFileTool,
        editFileTool,
        patchFileTool,
        runCommandTool,
        createLoadSkillTool(args.cwd),
        webFetchTool,
        webSearchTool,
      ]

  return new ToolRegistry(localTools, {
    skills,
    mcpServers: buildConnectingMcpSummaries(mcpServers),
  })
}

export async function hydrateMcpTools(args: {
  cwd: string
  runtime: RuntimeConfig | null
  tools: ToolRegistry
  profile?: ToolProfile
}): Promise<void> {
  const profile = args.profile ?? 'coding'
  const mcp = await createMcpBackedTools({
    cwd: args.cwd,
    mcpServers: args.runtime?.mcpServers ?? {},
    allowedServerNames: profile === 'tcm-consultation'
      ? TCM_CONSULTATION_MCP_SERVERS
      : undefined,
    includeAuxiliaryTools: profile !== 'tcm-consultation',
  })
  args.tools.addTools(mcp.tools)
  args.tools.setMcpServers(mcp.servers)
  args.tools.addDisposer(mcp.dispose)
}
