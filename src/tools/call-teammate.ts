import { z } from 'zod'
import type { ToolDefinition } from '../tool.js'
import { TCM_EXPERTS } from '../agents/tcm-experts.js'
import { loadRuntimeConfig } from '../config.js'
import { AnthropicModelAdapter } from '../anthropic-adapter.js'
import { OpenAIModelAdapter } from '../openai-adapter.js'
import { ToolRegistry } from '../tool.js'
import type { ChatMessage } from '../types.js'

type Input = {
  expertName: string
  query: string
}

export const callTeammateTool: ToolDefinition<Input> = {
  name: 'call_teammate',
  description: '中医专家联合会诊工具。可以呼叫其他垂类中医专家（如中医典籍研读专家、中药性味归经专家、配伍安全审查专家）进行单轮会诊，获取其诊断与评估建议。',
  inputSchema: {
    type: 'object',
    properties: {
      expertName: {
        type: 'string',
        description: '被呼叫的中医专家代号，可选值: classic_book_expert (典籍研读专家), herbology_expert (性味归经专家), safety_expert (配伍安全审查专家)',
      },
      query: {
        type: 'string',
        description: '需要咨询专家的中医临床病历、主诉或拟用处方等具体问题。',
      },
    },
    required: ['expertName', 'query'],
  },
  schema: z.object({
    expertName: z.string(),
    query: z.string(),
  }),
  async run(input, _context) {
    const expert = TCM_EXPERTS[input.expertName]
    if (!expert) {
      return {
        ok: false,
        output: `呼叫失败：未找到代号为 [${input.expertName}] 的中医专家。可选值包括: ${Object.keys(TCM_EXPERTS).join(', ')}`,
      }
    }

    try {
      const runtime = await loadRuntimeConfig()
      const isAnthropicNative = runtime?.baseUrl?.includes('anthropic.com') ?? false

      // 定制子智能体的模型参数，重写其推理随机性 (temperature)
      const getCustomRuntimeConfig = async () => {
        const conf = await loadRuntimeConfig()
        return {
          ...conf,
          temperature: expert.temperature,
        }
      }

      // 子智能体采用沙盒隔离（使用空的工具注册中心，不允许其调用外部 shell / 文件系统）
      const emptyTools = new ToolRegistry([])
      const subModel = isAnthropicNative
        ? new AnthropicModelAdapter(emptyTools, getCustomRuntimeConfig)
        : new OpenAIModelAdapter(emptyTools, getCustomRuntimeConfig)

      const messages: ChatMessage[] = [
        {
          role: 'system',
          content: expert.systemPrompt,
        },
        {
          role: 'user',
          content: input.query,
        },
      ]

      // 执行子智能体的单轮推理
      const result = await subModel.next(messages)

      if (result.type === 'assistant' && result.content) {
        return {
          ok: true,
          output: result.content,
        }
      } else {
        return {
          ok: false,
          output: '专家正在沉思，未能给出有效会诊结论。',
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      return {
        ok: false,
        output: `呼叫专家发生异常: ${errorMsg}`,
      }
    }
  },
}
