/**
 * 游戏公共库 - 三个游戏共用的逻辑
 */

// ============ WebSocket 客户端 ============
class GameWSClient {
  constructor(url = `ws://${window.location.host}/ws`) {
    this.url = url;
    this.ws = null;
    this.messageId = 0;
    this.pendingAcks = {};
    this.handlers = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        this.ws.onopen = () => {
          console.log('[WS] Connected');
          this.reconnectAttempts = 0;
          resolve();
        };
        this.ws.onmessage = (e) => this._handleMessage(JSON.parse(e.data));
        this.ws.onerror = (err) => {
          console.error('[WS] Error:', err);
          reject(err);
        };
        this.ws.onclose = () => this._handleClose();
      } catch (err) {
        reject(err);
      }
    });
  }

  send(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      console.warn('[WS] Not connected, message dropped:', msg);
    }
  }

  // 发送消息并等待确认
  async sendWithAck(msg, timeout = 5000) {
    const msgId = ++this.messageId;
    msg.msg_id = msgId;

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        delete this.pendingAcks[msgId];
        reject(new Error(`Message ${msgId} timeout after ${timeout}ms`));
      }, timeout);

      this.pendingAcks[msgId] = (response) => {
        clearTimeout(timer);
        resolve(response);
      };

      this.send(msg);
    });
  }

  on(type, handler) {
    if (!this.handlers[type]) {
      this.handlers[type] = [];
    }
    this.handlers[type].push(handler);
  }

  off(type, handler) {
    if (this.handlers[type]) {
      this.handlers[type] = this.handlers[type].filter(h => h !== handler);
    }
  }

  _handleMessage(msg) {
    // 处理确认
    if (msg.msg_id && this.pendingAcks[msg.msg_id]) {
      this.pendingAcks[msg.msg_id](msg);
      delete this.pendingAcks[msg.msg_id];
      return;
    }

    // 触发处理器
    if (this.handlers[msg.type]) {
      this.handlers[msg.type].forEach(h => h(msg));
    }
  }

  _handleClose() {
    console.log('[WS] Disconnected');
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect().catch(console.error), delay);
    }
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// ============ 工具函数 ============

// HTML 转义
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 安全的 DOM 文本设置
function setTextContent(element, text) {
  if (element) {
    element.textContent = text;
  }
}

// 安全的 DOM HTML 设置（仅用于可信内容）
function setInnerHTML(element, html) {
  if (element) {
    element.innerHTML = html;
  }
}

// Toast 通知
function showToast(message, duration = 2000) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// 生成唯一 ID
function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// 格式化时间
function formatTime(date = new Date()) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 格式化金额
function formatMoney(amount) {
  return `$${amount.toLocaleString()}`;
}

// ============ 状态管理 ============

class GameState {
  constructor() {
    this.state = null;
    this.version = 0;
    this.listeners = [];
  }

  update(newState) {
    const oldState = this.state;
    this.state = newState;
    this.version = newState.version || this.version + 1;

    // 通知所有监听器
    this.listeners.forEach(listener => {
      try {
        listener(newState, oldState);
      } catch (err) {
        console.error('State listener error:', err);
      }
    });
  }

  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  get(path) {
    if (!path) return this.state;
    return path.split('.').reduce((obj, key) => obj?.[key], this.state);
  }
}

// ============ 输入验证 ============

const Validators = {
  playerName(name) {
    if (!name || typeof name !== 'string') return false;
    if (name.length < 1 || name.length > 20) return false;
    return /^[a-zA-Z0-9_\-一-鿿]+$/.test(name);
  },

  amount(amount) {
    if (typeof amount !== 'number') return false;
    return amount > 0 && amount <= 999999 && Number.isInteger(amount);
  },

  roomId(roomId) {
    if (!roomId || typeof roomId !== 'string') return false;
    return /^[a-zA-Z0-9]{6,}$/.test(roomId);
  },

  message(msg) {
    if (!msg || typeof msg !== 'string') return false;
    return msg.length > 0 && msg.length <= 200;
  }
};

// ============ 错误处理 ============

class GameError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
    this.name = 'GameError';
  }
}

class ValidationError extends GameError {
  constructor(message) {
    super('VALIDATION_ERROR', message);
    this.name = 'ValidationError';
  }
}

class GameStateError extends GameError {
  constructor(message) {
    super('STATE_ERROR', message);
    this.name = 'GameStateError';
  }
}

// 错误处理器
function handleError(error) {
  console.error('[Error]', error);

  if (error instanceof ValidationError) {
    showToast(`输入错误: ${error.message}`);
  } else if (error instanceof GameStateError) {
    showToast(`游戏状态错误: ${error.message}`);
  } else if (error instanceof GameError) {
    showToast(`游戏错误: ${error.message}`);
  } else {
    showToast('发生错误，请重试');
  }
}

// ============ 存储管理 ============

const Storage = {
  set(key, value) {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch (err) {
      console.error('Storage set error:', err);
    }
  },

  get(key) {
    try {
      const value = sessionStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    } catch (err) {
      console.error('Storage get error:', err);
      return null;
    }
  },

  remove(key) {
    try {
      sessionStorage.removeItem(key);
    } catch (err) {
      console.error('Storage remove error:', err);
    }
  },

  clear() {
    try {
      sessionStorage.clear();
    } catch (err) {
      console.error('Storage clear error:', err);
    }
  }
};

// ============ 事件总线 ============

class EventBus {
  constructor() {
    this.events = {};
  }

  on(event, handler) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (this.events[event]) {
      this.events[event] = this.events[event].filter(h => h !== handler);
    }
  }

  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(handler => {
        try {
          handler(data);
        } catch (err) {
          console.error(`Event handler error for ${event}:`, err);
        }
      });
    }
  }

  clear() {
    this.events = {};
  }
}

// 全局事件总线
const eventBus = new EventBus();

// ============ 导出 ============
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    GameWSClient,
    GameState,
    GameError,
    ValidationError,
    GameStateError,
    Validators,
    Storage,
    EventBus,
    eventBus,
    escapeHtml,
    setTextContent,
    setInnerHTML,
    showToast,
    generateId,
    formatTime,
    formatMoney,
    handleError
  };
}
