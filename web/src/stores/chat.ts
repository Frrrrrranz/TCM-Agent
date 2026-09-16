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

interface WebSocketFrame {
  protocolVersion: 1
  type: string
  sessionId?: string
  requestId?: string
  sequence: number
  toolUseId?: string
  content?: string
  toolName?: string
  input?: unknown
  output?: string
  isError?: boolean
  messages?: Message[]
  modelName?: string
  streaming?: boolean
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
  let outgoingSequence = 0
  let connectedSessionId = ''
  let activeRequestId: string | null = null
  let activeRequestSessionId: string | null = null
  let pendingAnswer = ''
  
  const currentSession = computed(() => {
    return sessions.value.find((s) => s.id === activeSessionId.value)
  })

  // 初始化默认会话
  if (sessions.value.length === 0) {
    createNewSession()
  }

  function createNewSession() {
    disconnectForSessionChange()
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

  function selectSession(id: string) {
    if (id === activeSessionId.value) return
    if (!sessions.value.some(session => session.id === id)) return
    disconnectForSessionChange()
    activeSessionId.value = id
  }

  function deleteSession(id: string) {
    const index = sessions.value.findIndex((s) => s.id === id)
    if (activeSessionId.value === id) disconnectForSessionChange()
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

  function disconnectForSessionChange() {
    const previousSocket = socket.value
    socket.value = null
    connectedSessionId = ''
    activeRequestId = null
    activeRequestSessionId = null
    pendingAnswer = ''
    isConnected.value = false
    isGenerating.value = false
    previousSocket?.close()
  }

  function initWebSocket(onReady?: () => void) {
    if (socket.value && connectedSessionId !== activeSessionId.value) {
      disconnectForSessionChange()
    }
    if (socket.value) {
      if (socket.value.readyState === WebSocket.OPEN) {
        onReady?.()
      } else if (socket.value.readyState === WebSocket.CONNECTING) {
        if (onReady) socket.value.addEventListener('open', onReady, { once: true })
      } else {
        disconnectForSessionChange()
      }
      if (socket.value) return
    }

    // 后端默认运行于 8000 端口
    outgoingSequence = 0
    const socketProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${socketProtocol}//${window.location.hostname}:8000/ws/chat?session_id=${encodeURIComponent(activeSessionId.value)}`
    const ws = new WebSocket(wsUrl)
    socket.value = ws
    connectedSessionId = activeSessionId.value

    ws.onopen = () => {
      if (socket.value !== ws) return
      isConnected.value = true
      if (onReady) onReady()
    }

    ws.onmessage = (event) => {
      if (socket.value !== ws) return
      try {
        const data = JSON.parse(event.data)
        handleStreamMessage(data)
      } catch (err) {
        console.error('处理 WebSocket 流数据报错:', err)
      }
    }

    ws.onclose = () => {
      if (socket.value !== ws) return
      socket.value = null
      connectedSessionId = ''
      activeRequestId = null
      activeRequestSessionId = null
      pendingAnswer = ''
      isConnected.value = false
      isGenerating.value = false
    }

    ws.onerror = (err) => {
      console.error('WebSocket 连接发生异常:', err)
    }
  }

  function sendPayload(content: string) {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return
    if (activeRequestId) return
    const requestId = crypto.randomUUID()
    activeRequestId = requestId
    activeRequestSessionId = activeSessionId.value
    pendingAnswer = ''
    socket.value.send(
      JSON.stringify({
        protocolVersion: 1,
        type: 'user_message',
        sessionId: activeSessionId.value,
        requestId,
        sequence: outgoingSequence++,
        content,
      })
    )
  }

  function sendMessage(text: string) {
    if (!text.trim()) return
    if (isGenerating.value) return

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
    // 4. 发送 WebSocket，如果连接未就绪则初始化后发送
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN || connectedSessionId !== activeSessionId.value) {
      initWebSocket(() => {
        sendPayload(text)
      })
    } else {
      sendPayload(text)
    }
  }

  function stopGenerating() {
    if (!activeRequestId || !activeRequestSessionId) {
      if (isGenerating.value) disconnectForSessionChange()
      return
    }
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) return
    socket.value.send(JSON.stringify({
      protocolVersion: 1,
      type: 'cancel_turn',
      sessionId: activeRequestSessionId,
      requestId: activeRequestId,
      sequence: outgoingSequence++,
    }))
  }

  function handleStreamMessage(data: unknown) {
    if (!data || typeof data !== 'object' || !('type' in data)) return
    const frame = data as WebSocketFrame
    if (frame.protocolVersion !== 1 || typeof frame.sequence !== 'number') return
    if (frame.type !== 'init' && frame.type !== 'heartbeat_ack') {
      if (
        !activeRequestId ||
        frame.requestId !== activeRequestId ||
        frame.sessionId !== activeRequestSessionId ||
        activeSessionId.value !== activeRequestSessionId
      ) return
    }
    const session = currentSession.value
    if (!session) return

    switch (frame.type) {
      case 'init':
        // 初始化时设置模型名称
        modelName.value = frame.modelName || modelName.value
        break

      case 'tool_start':
        // 添加工具调用中药丸
        session.messages.push({
          role: 'assistant_tool_call',
          toolUseId: frame.toolUseId,
          toolName: frame.toolName,
          input: frame.input,
          isError: false,
        })
        break

      case 'tool_result':
        // 添加工具调用结果
        session.messages.push({
          role: 'tool_result',
          toolUseId: frame.toolUseId,
          toolName: frame.toolName,
          output: frame.output,
          isError: frame.isError,
        })
        break

      case 'progress_message':
        // AI 产生的流式中间状态进度
        session.messages.push({
          role: 'assistant_progress',
          content: frame.content,
        })
        break

      case 'assistant_message': {
        // NOTE: 未验收的医疗建议不以 Token 增量公开；最终消息仍由服务端权威快照提供。
        if (frame.streaming) pendingAnswer = (pendingAnswer + (frame.content || '')).slice(-12000)
        break
      }

      case 'turn_complete':
        // 渲染结束，利用后端最标准的 messages 对话链覆盖同步
        if (frame.messages && frame.messages.length > 0) {
          // 在覆盖时保留 system 角色，并提取 token 消耗
          const cleanMsgs = frame.messages
          
          // 保留系统初始进度
          const initProgress = session.messages.filter(
            (m) => m.role === 'assistant_progress' && m.content?.includes('> Ready')
          )
          
          session.messages = [...initProgress, ...cleanMsgs]

          // 提取 token 统计信息
          const lastAssistant = [...frame.messages]
            .reverse()
            .find((m) => m.role === 'assistant' && m.providerUsage)
          if (lastAssistant && lastAssistant.providerUsage) {
            tokensUsed.value = lastAssistant.providerUsage.totalTokens || tokensUsed.value
          }
        }
        isGenerating.value = false
        activeRequestId = null
        activeRequestSessionId = null
        pendingAnswer = ''
        break

      case 'cancel_requested':
        break

      case 'turn_cancelled':
        isGenerating.value = false
        activeRequestId = null
        activeRequestSessionId = null
        pendingAnswer = ''
        break

      case 'error':
        // 处理运行错误
        session.messages.push({
          role: 'assistant',
          content: `⚠️ [系统错误] ${frame.content || 'unknown_error'}`,
          isError: true,
        })
        isGenerating.value = false
        activeRequestId = null
        activeRequestSessionId = null
        pendingAnswer = ''
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
    selectSession,
    deleteSession,
    sendMessage,
    stopGenerating,
    initWebSocket,
  }
})
