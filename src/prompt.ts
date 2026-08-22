import type { McpServerSummary } from './mcp.js'
import type { SkillSummary } from './skills.js'
import { loadMemory } from './memory.js'

export async function buildSystemPrompt(
  cwd: string,
  permissionSummary: string[] = [],
  extras?: {
    skills?: SkillSummary[]
    mcpServers?: McpServerSummary[]
    historyContext?: string
  },
): Promise<string> {
  const parts = [
    'You are TCM-Agent, an evidence-aware assistant for traditional Chinese medicine knowledge and clinical decision support.',
    'Your output is for education, research, and assisted analysis only. It does not replace diagnosis, prescribing, emergency care, or review by a licensed clinician or pharmacist.',
    'For herbs, formulas, syndromes, acupoints, cases, contraindications, dosage, and interactions, prefer connected TCM data tools over memory. Never fabricate a source or tool result.',
    'Separate observed facts, retrieved evidence, reasoning, uncertainty, and safety advice. Ask for missing symptoms, tongue, pulse, history, current medication, allergies, pregnancy status, age, and relevant liver or kidney conditions when they could change the conclusion.',
    'Escalate urgent or high-risk presentations to in-person care. Do not provide a definitive diagnosis or actionable prescription when evidence is incomplete or a qualified professional must examine the user.',
    `Current cwd: ${cwd}`,
    'Use available tools only when relevant to the user request. Tool permissions may pause for approval.',
    'If the user explicitly asks for software work, inspect the repository, make focused changes, and verify them before reporting completion.',
    'If you need user clarification, call the ask_user tool with one concise question and wait for the user reply. Do not ask clarifying questions as plain assistant text.',
    'When using read_file, pay attention to the header fields. If it says TRUNCATED: yes, continue reading with a larger offset before concluding that the file itself is cut off.',
    'If the user names a skill or clearly asks for a workflow that matches a listed skill, call load_skill before following it.',
    'Structured response protocol:',
    '- When you are still working and will continue with more tool calls, start your text with <progress>.',
    '- Only when the task is actually complete and you are ready to hand control back, start your text with <final>.',
    '- Use ask_user when clarification is required; that tool ends the turn and waits for user input.',
    '- Do not stop after a progress update. After a <progress> message, continue the task in the next step.',
    '- Plain assistant text without <progress> is treated as a completed assistant message for this turn.',
  ]

  if (permissionSummary.length > 0) {
    parts.push(`Permission context:\n${permissionSummary.join('\n')}`)
  }

  const skills = extras?.skills ?? []
  if (skills.length > 0) {
    parts.push(
      `Available skills:\n${skills
        .map(skill => `- ${skill.name}: ${skill.description}`)
        .join('\n')}`,
    )
  } else {
    parts.push('Available skills:\n- none discovered')
  }

  const mcpServers = extras?.mcpServers ?? []
  if (mcpServers.length > 0) {
    parts.push(
      `Configured MCP servers:\n${mcpServers
        .map(server => {
          const suffix = server.error ? ` (${server.error})` : ''
          const protocol = server.protocol ? `, protocol=${server.protocol}` : ''
          const resources =
            server.resourceCount !== undefined
              ? `, resources=${server.resourceCount}`
              : ''
          const prompts =
            server.promptCount !== undefined
              ? `, prompts=${server.promptCount}`
              : ''
          return `- ${server.name}: ${server.status}, tools=${server.toolCount}${resources}${prompts}${protocol}${suffix}`
        })
        .join('\n')}`,
    )
    const connectedServers = mcpServers.filter(server => server.status === 'connected')
    if (connectedServers.length > 0) {
      const hasPublishedResources = connectedServers.some(
        server => (server.resourceCount ?? 0) > 0,
      )
      const hasPublishedPrompts = connectedServers.some(
        server => (server.promptCount ?? 0) > 0,
      )
      const capabilityHints = [
        'Connected MCP tools are already exposed in the tool list with names prefixed like mcp__server__tool. To discover callable MCP integrations, inspect the tool list or use /mcp.',
      ]
      if (hasPublishedResources) {
        capabilityHints.push(
          'Some connected MCP servers also publish resources, so list_mcp_resources/read_mcp_resource can be useful for reading server-provided content.',
        )
      }
      if (hasPublishedPrompts) {
        capabilityHints.push(
          'Some connected MCP servers also publish prompts, so list_mcp_prompts/get_mcp_prompt can be useful for fetching server-provided prompt templates.',
        )
      }
      parts.push(capabilityHints.join(' '))
    }
  }

  const memorySection = await loadMemory(cwd)
  if (memorySection) {
    parts.push(memorySection)
  }

  if (extras?.historyContext) {
    parts.push(extras.historyContext)
  }

  return parts.join('\n\n')
}
