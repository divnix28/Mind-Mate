/**
 * Mind-Mate Student Chat Client
 * Real-time 3-Tier WebSocket Interface
 */

(function () {
  'use strict';

  // DOM Elements
  const messagesContainer = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const connectionBeacon = document.getElementById('connectionBeacon');
  const beaconStatusText = document.getElementById('beaconStatusText');
  const handlerBadge = document.getElementById('handlerBadge');
  const handlerText = document.getElementById('handlerText');
  const sessionTag = document.getElementById('sessionTag');
  const emergencyBanner = document.getElementById('emergencyBanner');
  const noSessionModal = document.getElementById('noSessionModal');
  const customSessionInput = document.getElementById('customSessionInput');
  const joinCustomSessionBtn = document.getElementById('joinCustomSessionBtn');

  // State
  let socket = null;
  let isFrozen = false;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 5;

  // 1. Session Detection (Dynamic, No Hardcoded Fallback)
  const urlParams = new URLSearchParams(window.location.search);
  let sessionId = urlParams.get('session_id') || sessionStorage.getItem('mindmate_student_session');

  if (!sessionId) {
    // Show modal to cleanly select or create a session, preventing hardcoded mock IDs
    if (noSessionModal) {
      noSessionModal.classList.add('active');
    }
  } else {
    initChat(sessionId);
  }

  // Handle modal input if session was not in URL
  if (joinCustomSessionBtn && customSessionInput) {
    joinCustomSessionBtn.addEventListener('click', () => {
      const enteredId = customSessionInput.value.trim();
      if (enteredId) {
        sessionStorage.setItem('mindmate_student_session', enteredId);
        window.location.search = `?session_id=${encodeURIComponent(enteredId)}`;
      }
    });

    customSessionInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        joinCustomSessionBtn.click();
      }
    });
  }

  function initChat(sId) {
    sessionId = sId;
    sessionStorage.setItem('mindmate_student_session', sId);
    if (sessionTag) {
      sessionTag.textContent = `SESSION #${sId}`;
    }

    connectWebSocket();
    bindInputEvents();
  }

  // 2. Dynamic WebSocket Routing (Protocol and Host agnostic)
  function connectWebSocket() {
    updateConnectionStatus('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/student/${sessionId}`;

    try {
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        reconnectAttempts = 0;
        updateConnectionStatus('connected');
        console.log(`[Mind-Mate WS] Connected securely to ${wsUrl}`);
      };

      socket.onmessage = (event) => {
        handleIncomingMessage(event.data);
      };

      socket.onerror = (err) => {
        console.error('[Mind-Mate WS] Socket error:', err);
      };

      socket.onclose = (event) => {
        console.warn(`[Mind-Mate WS] Disconnected. Code: ${event.code}`);
        updateConnectionStatus('disconnected');

        // If not deliberately frozen or closed due to invalid session
        if (!isFrozen && event.code !== 1008 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts++;
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
          beaconStatusText.textContent = `Reconnecting in ${timeout / 1000}s...`;
          setTimeout(connectWebSocket, timeout);
        } else if (event.code === 1008) {
          appendSystemMessage(
            'Session closed by server: Session ID not found in database. Please check your session ID or start a new one.',
            'error'
          );
        }
      };
    } catch (e) {
      console.error('[Mind-Mate WS] Connection error:', e);
      updateConnectionStatus('disconnected');
    }
  }

  // 3. Message Routing & State Workflow Handler
  function handleIncomingMessage(rawData) {
    try {
      const data = JSON.parse(rawData);

      // Backend formats:
      // Phase 1 (Bot): {"sender": "BOT", "content": "..."}
      // Phase 2 (Handoff): {"sender": "SYSTEM", "content": "Routing you to a human counselor..."}
      // Phase 3 (Counselor): {"sender": "COUNSELOR", "content": "..."}
      // Phase 4 (SOS): {"sender": "SYSTEM", "content": "Help is on the way..."}

      const sender = (data.sender || '').toUpperCase();
      const content = data.content || '';

      if (sender === 'BOT') {
        appendBotMessage(content);
        updateHandlerState('bot', 'AI Triage Companion');
      } else if (sender === 'COUNSELOR') {
        appendCounselorMessage(content);
        updateHandlerState('counselor', 'Human Counselor Active');
      } else if (sender === 'SYSTEM') {
        handleSystemEvent(content);
      } else {
        // Fallback for custom or direct text
        appendBotMessage(content || rawData);
      }
    } catch (err) {
      // Plain text fallback
      console.warn('Non-JSON message received:', rawData);
      appendBotMessage(rawData);
    }
  }

  function handleSystemEvent(content) {
    const isHandoff = content.toLowerCase().includes('routing you to a human counselor');
    const isSOS = content.toLowerCase().includes('help is on the way');

    if (isHandoff) {
      // Phase 2: Handoff to human counselor
      updateHandlerState('counselor', 'Handoff in Progress...');
      appendSystemMessage(
        'A licensed campus counselor is being notified and connected to this safe channel. You remain completely anonymous.',
        'handoff'
      );
    } else if (isSOS) {
      // Phase 4: Emergency SOS Triggered -> Freeze chat!
      freezeChat();
      updateHandlerState('sos', 'Emergency Protocol Active');
      appendSystemMessage(content, 'sos-alert');
    } else {
      appendSystemMessage(content, 'info');
    }
  }

  // 4. Freeze Chat Logic for Emergency Phase 4
  function freezeChat() {
    isFrozen = true;
    chatInput.disabled = true;
    sendBtn.disabled = true;
    chatInput.value = '';
    chatInput.placeholder = 'Chat frozen for emergency dispatch. Campus support is on the way.';

    const inputBox = document.querySelector('.chat-input-box');
    if (inputBox) {
      inputBox.classList.add('frozen');
    }

    if (emergencyBanner) {
      emergencyBanner.classList.add('active');
    }
  }

  // 5. DOM Rendering Helpers
  function appendStudentMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row student';

    const timeStr = getCurrentTime();

    row.innerHTML = `
      <div class="message-bubble-wrapper">
        <div class="message-sender-name">You (Anonymous)</div>
        <div class="message-bubble">${escapeHtml(text)}</div>
        <div class="message-timestamp">${timeStr}</div>
      </div>
      <div class="message-avatar student">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendBotMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row bot';

    const timeStr = getCurrentTime();

    row.innerHTML = `
      <div class="message-avatar bot">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="10" rx="2"></rect>
          <circle cx="12" cy="5" r="2"></circle>
          <path d="M12 7v4"></path>
          <line x1="8" y1="16" x2="8" y2="16"></line>
          <line x1="16" y1="16" x2="16" y2="16"></line>
        </svg>
      </div>
      <div class="message-bubble-wrapper">
        <div class="message-sender-name">Mind-Mate AI Companion</div>
        <div class="message-bubble">${formatMarkdown(text)}</div>
        <div class="message-timestamp">${timeStr}</div>
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendCounselorMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row counselor';

    const timeStr = getCurrentTime();

    row.innerHTML = `
      <div class="message-avatar counselor">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
          <path d="M12 11v6"></path>
          <path d="M9 14h6"></path>
        </svg>
      </div>
      <div class="message-bubble-wrapper">
        <div class="message-sender-name">
          Campus Counselor
          <span class="counselor-pill">Verified Staff</span>
        </div>
        <div class="message-bubble">${formatMarkdown(text)}</div>
        <div class="message-timestamp">${timeStr}</div>
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  function appendSystemMessage(text, type = 'info') {
    const row = document.createElement('div');
    row.className = 'message-row system';

    let iconHtml = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
    `;

    if (type === 'handoff') {
      iconHtml = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
          <circle cx="8.5" cy="7" r="4"></circle>
          <polyline points="17 11 19 13 23 9"></polyline>
        </svg>
      `;
    } else if (type === 'sos-alert') {
      iconHtml = `
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      `;
    }

    row.innerHTML = `
      <div class="system-message-card ${type}">
        <div class="system-icon">${iconHtml}</div>
        <div>${escapeHtml(text)}</div>
      </div>
    `;

    messagesContainer.appendChild(row);
    scrollToBottom();
  }

  // 6. User Send Action
  function sendMessage() {
    if (isFrozen) return;

    const messageText = chatInput.value.trim();
    if (!messageText) return;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      appendSystemMessage('Unable to send: connection is not open. Reconnecting...', 'error');
      return;
    }

    // Append to student chat UI immediately
    appendStudentMessage(messageText);

    // Send raw text to backend WebSocket endpoint
    socket.send(messageText);

    // Reset input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatInput.focus();
  }

  function bindInputEvents() {
    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-expand textarea
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
    });

    // Quick prompt chip listeners
    document.querySelectorAll('.prompt-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        if (isFrozen) return;
        chatInput.value = chip.getAttribute('data-prompt') || chip.textContent.trim();
        sendMessage();
      });
    });
  }

  // 7. Status Helpers
  function updateConnectionStatus(status) {
    if (!connectionBeacon || !beaconStatusText) return;

    connectionBeacon.className = 'status-beacon';

    if (status === 'connected') {
      connectionBeacon.classList.add('live');
      beaconStatusText.textContent = 'Connected';
    } else if (status === 'connecting') {
      connectionBeacon.classList.add('awaiting');
      beaconStatusText.textContent = 'Connecting...';
    } else {
      connectionBeacon.classList.add('critical');
      beaconStatusText.textContent = 'Disconnected';
    }
  }

  function updateHandlerState(type, text) {
    if (!handlerBadge || !handlerText) return;

    handlerBadge.className = 'handler-badge ' + type;
    handlerText.textContent = text;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    let escaped = escapeHtml(text);
    // Bold
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Line breaks
    escaped = escaped.replace(/\n/g, '<br/>');
    return escaped;
  }
})();
