import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Message {
  role:
    | 'system'
    | 'user'
    | 'assistant_thinking'
    | 'assistant'
    | 'assistant_progress'
    | 'assistant_tool_call'
    | 'tool_result'
    | 'context_summary'
    | 'snip_boundary'
  content?: string
  toolUseId?: string
  toolName?: string
  input?: any
  output?: string
  isError?: boolean
  blocks?: any[]
  providerUsage?: {
    inputTokens: number
    outputTokens: number
    totalTokens: number
  }
}

export interface Session {
  id: string
  title: string
  messages: Message[]
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<Session[]>([])
  const activeSessionId = ref<string>('')
  const isConnected = ref<boolean>(false)
  const isGenerating = ref<boolean>(false)
  // NOTE: 默认值仅用于 init 帧到达前的占位显示，真实模型名由后端 init 帧动态推送
  const modelName = ref<string>('TCM-Agent')
  
  // 用于顶部的 Token 用量指示器
  const tokensUsed = ref<number>(0)
  const tokensLimit = ref<number>(200000)

  const socket = ref<WebSocket | null>(null)
  
  const currentSession = computed(() => {
    return sessions.value.find((s) => s.id === activeSessionId.value)
  })

  // 初始化默认会话
  if (sessions.value.length === 0) {
    createNewSession()
  }

  function createNewSession() {
    const id = Math.random().toString(36).substring(2, 10)
    const newSession: Session = {
      id,
      title: `Discussion: ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      messages: [
        {
          role: 'assistant_progress',
          content: '> Diagnostic module loaded.\n> Knowledge base: Shanghan Lun, Jin Gui Yao Lue connected.\n> Ready for input.',
        },
      ],
    }
    sessions.value.push(newSession)
    activeSessionId.value = id
  }

  function deleteSession(id: string) {
    const index = sessions.value.findIndex((s) => s.id === id)
    if (index !== -1) {
      sessions.value.splice(index, 1)
      if (activeSessionId.value === id) {
        if (sessions.value.length > 0) {
          const lastSession = sessions.value[sessions.value.length - 1]
          activeSessionId.value = lastSession ? lastSession.id : ''
        } else {
          createNewSession()
        }
      }
    }
  }

  function initWebSocket(onReady?: () => void) {
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
      if (onReady) onReady()
      return
    }

    // 后端默认运行于 8000 端口
    const wsUrl = `ws://${window.location.hostname}:8000/ws/chat`
    const ws = new WebSocket(wsUrl)
    socket.value = ws

    ws.onopen = () => {
      isConnected.value = true
      console.log('WebSocket 连接已打通')
      if (onReady) onReady()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleStreamMessage(data)
      } catch (err) {
        console.error('处理 WebSocket 流数据报错:', err)
      }
    }

    ws.onclose = () => {
      isConnected.value = false
      isGenerating.value = false
      console.log('WebSocket 连接关闭，正在自动重连...')
    }

    ws.onerror = (err) => {
      console.error('WebSocket 连接发生异常:', err)
    }
  }

  function sendPayload(content: string, history: Message[]) {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return
    socket.value.send(
      JSON.stringify({
        content,
        history,
      })
    )
  }

  function sendMessage(text: string) {
    if (!text.trim()) return

    const session = currentSession.value
    if (!session) return

    // 1. 追加用户消息
    session.messages.push({
      role: 'user',
      content: text,
    })

    // 2. 自动修正会话的标题
    if (session.title.startsWith('Discussion:') || session.title === 'New Chat') {
      session.title = text.length > 15 ? text.substring(0, 15) + '...' : text
    }

    isGenerating.value = true

    // 3. 构建发送历史（剔除 system 角色以减少网络开销）
    const historyPayload = session.messages.filter((m) => m.role !== 'system')

    // 4. 发送 WebSocket，如果连接未就绪则初始化后发送
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      initWebSocket(() => {
        sendPayload(text, historyPayload)
      })
    } else {
      sendPayload(text, historyPayload)
    }
  }

  function handleStreamMessage(data: any) {
    const session = currentSession.value
    if (!session) return

    switch (data.type) {
      case 'init':
        // 初始化时设置模型名称
        modelName.value = data.modelName
        break

      case 'tool_start':
        // 添加工具调用中药丸
        session.messages.push({
          role: 'assistant_tool_call',
          toolName: data.toolName,
          input: data.input,
          isError: false,
        })
        break

      case 'tool_result':
        // 添加工具调用结果
        session.messages.push({
          role: 'tool_result',
          toolName: data.toolName,
          output: data.output,
          isError: data.isError,
        })
        break

      case 'progress_message':
        // AI 产生的流式中间状态进度
        session.messages.push({
          role: 'assistant_progress',
          content: data.content,
        })
        break

      case 'assistant_message': {
        // AI 流式生成文本响应，直接拼接到最后一个 assistant 消息
        const lastMsg = session.messages[session.messages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = (lastMsg.content || '') + data.content
        } else {
          session.messages.push({
            role: 'assistant',
            content: data.content,
          })
        }
        break
      }

      case 'turn_complete':
        // 渲染结束，利用后端最标准的 messages 对话链覆盖同步
        if (data.messages && data.messages.length > 0) {
          // 在覆盖时保留 system 角色，并提取 token 消耗
          const cleanMsgs = data.messages
          
          // 保留系统初始进度
          const initProgress = session.messages.filter(
            (m) => m.role === 'assistant_progress' && m.content?.includes('> Ready')
          )
          
          session.messages = [...initProgress, ...cleanMsgs]

          // 提取 token 统计信息
          const lastAssistant = [...data.messages]
            .reverse()
            .find((m: any) => m.role === 'assistant' && m.providerUsage)
          if (lastAssistant && lastAssistant.providerUsage) {
            tokensUsed.value = lastAssistant.providerUsage.totalTokens || tokensUsed.value
          }
        }
        isGenerating.value = false
        break

      case 'error':
        // 处理运行错误
        session.messages.push({
          role: 'assistant',
          content: `⚠️ [系统错误] ${data.content}`,
          isError: true,
        })
        isGenerating.value = false
        break
    }
  }

  return {
    sessions,
    activeSessionId,
    isConnected,
    isGenerating,
    modelName,
    tokensUsed,
    tokensLimit,
    currentSession,
    createNewSession,
    deleteSession,
    sendMessage,
    initWebSocket,
  }
})
