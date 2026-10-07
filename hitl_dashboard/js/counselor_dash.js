/**
 * Mind-Mate Counselor Command Dashboard
 * Real-Time HITL (Human-in-the-Loop) WebSocket Triage & Emergency SOS Dispatcher
 */

(function () {
  'use strict';

  // State Management
  let activeSessionId = null;
  let counselorSocket = null;
  let activeSessionsQueue = [
    // Pre-populated initial queue items for instant triage accessibility
    {
      id: 1,
      status: 'AWAITING_COUNSELOR',
      timestamp: new Date(Date.now() - 3 * 60000),
      preview: 'Escalated by AI: Moderate distress score detected. Needs human active listening.',
      riskTier: 2
    }
  ];

  // DOM Elements
  const queueContainer = document.getElementById('queueItems');
  const queueCountBadge = document.getElementById('queueCount');
  const emptyStateView = document.getElementById('emptyStateView');
  const activeChatView = document.getElementById('activeChatView');
  const chatStream = document.getElementById('counselorChatStream');
  const counselorInput = document.getElementById('counselorInput');
  const counselorSendBtn = document.getElementById('counselorSendBtn');
  const activeSessionTitle = document.getElementById('activeSessionTitle');
  const activeStatusBeacon = document.getElementById('activeStatusBeacon');
  const activeStatusText = document.getElementById('activeStatusText');
  const sosBreakGlassBtn = document.getElementById('sosBreakGlassBtn');
  const quickConnectInput = document.getElementById('quickConnectInput');
  const quickConnectBtn = document.getElementById('quickConnectBtn');

  // SOS Modal Elements
  const sosModal = document.getElementById('sosModal');
  const sosStudentName = document.getElementById('sosStudentName');
  const sosRegNo = document.getElementById('sosRegNo');
  const sosLocation = document.getElementById('sosLocation');
  const sosPhone = document.getElementById('sosPhone');
  const sosCallLink = document.getElementById('sosCallLink');
  const copySosBtn = document.getElementById('copySosBtn');
  const closeSosBtn = document.getElementById('closeSosBtn');

  // Confirm Dispatch Modal
  const confirmSosModal = document.getElementById('confirmSosModal');
  const confirmSosProceedBtn = document.getElementById('confirmSosProceedBtn');
  const cancelSosBtn = document.getElementById('cancelSosBtn');

  // Initialization
  document.addEventListener('DOMContentLoaded', () => {
    renderQueue();
    bindEvents();
    checkUrlForSession();
  });

  function checkUrlForSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionParam = urlParams.get('session_id');
    if (sessionParam) {
      const parsedId = parseInt(sessionParam, 10);
      if (!isNaN(parsedId)) {
        joinSession(parsedId);
      }
    }
  }

  function bindEvents() {
    // Quick Connect by ID
    if (quickConnectBtn && quickConnectInput) {
      quickConnectBtn.addEventListener('click', () => {
        const id = parseInt(quickConnectInput.value.trim(), 10);
        if (!isNaN(id) && id > 0) {
          joinSession(id);
          quickConnectInput.value = '';
        }
      });

      quickConnectInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          quickConnectBtn.click();
        }
      });
    }

    // Counselor message send
    if (counselorSendBtn && counselorInput) {
      counselorSendBtn.addEventListener('click', sendCounselorMessage);

      counselorInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendCounselorMessage();
        }
      });

      // Auto-expand textarea
      counselorInput.addEventListener('input', () => {
        counselorInput.style.height = 'auto';
        counselorInput.style.height = Math.min(counselorInput.scrollHeight, 140) + 'px';
      });
    }

    // Clinical canned response chips
    document.querySelectorAll('.clinical-prompt-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        if (!activeSessionId) return;
        counselorInput.value = chip.getAttribute('data-text') || chip.textContent.trim();
        counselorInput.focus();
      });
    });

    // 🚨 SOS BREAK-GLASS BUTTON TRIGGER
    if (sosBreakGlassBtn) {
      sosBreakGlassBtn.addEventListener('click', () => {
        if (!activeSessionId) return;
        // Show confirmation before breaking PII seal
        if (confirmSosModal) {
          confirmSosModal.classList.add('active');
        } else {
          executeSosUnmask(activeSessionId);
        }
      });
    }

    if (confirmSosProceedBtn) {
      confirmSosProceedBtn.addEventListener('click', () => {
        if (confirmSosModal) confirmSosModal.classList.remove('active');
        if (activeSessionId) {
          executeSosUnmask(activeSessionId);
        }
      });
    }

    if (cancelSosBtn) {
      cancelSosBtn.addEventListener('click', () => {
        if (confirmSosModal) confirmSosModal.classList.remove('active');
      });
    }

    // SOS Modal Close
    if (closeSosBtn) {
      closeSosBtn.addEventListener('click', () => {
        if (sosModal) sosModal.classList.remove('active');
      });
    }

    // Copy SOS Record
    if (copySosBtn) {
      copySosBtn.addEventListener('click', () => {
        const textToCopy = `EMERGENCY DISPATCH DOSSIER:\nStudent: ${sosStudentName.textContent}\nReg No: ${sosRegNo.textContent}\nLocation: ${sosLocation.textContent}\nPhone: ${sosPhone.textContent}\nSession: #${activeSessionId}`;
        navigator.clipboard.writeText(textToCopy).then(() => {
          copySosBtn.textContent = '✓ Copied to Clipboard';
          setTimeout(() => {
            copySosBtn.textContent = 'Copy Dispatch Dossier';
          }, 3000);
        });
      });
    }
  }

  // ========================================================
  // 1. Session Queue Management
  // ========================================================
  function renderQueue() {
    if (!queueContainer) return;
    queueContainer.innerHTML = '';

    const awaitingCount = activeSessionsQueue.filter((s) => s.status === 'AWAITING_COUNSELOR').length;
    if (queueCountBadge) {
      queueCountBadge.textContent = `${awaitingCount} Awaiting`;
    }

    if (activeSessionsQueue.length === 0) {
      queueContainer.innerHTML = `
        <div class="queue-empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <p>No escalated sessions in queue.<br/>All campus triage channels normal.</p>
        </div>
      `;
      return;
    }

    activeSessionsQueue.forEach((session) => {
      const card = document.createElement('div');
      card.className = `session-card ${session.status.toLowerCase().replace('_', '-')}`;
      if (session.id === activeSessionId) {
        card.classList.add('active-session');
      }

      const elapsed = formatElapsed(session.timestamp);

      card.innerHTML = `
        <div class="card-top">
          <span class="card-session-id">SESSION #${session.id}</span>
          <span class="card-status-pill ${session.status === 'AWAITING_COUNSELOR' ? 'awaiting' : session.status === 'CRITICAL_SOS' ? 'sos' : 'live'}">
            ${session.status.replace('_', ' ')}
          </span>
        </div>
        <div class="card-body">
          <div class="card-preview-text">${escapeHtml(session.preview)}</div>
        </div>
        <div class="card-footer">
          <span>Escalated ${elapsed}</span>
          <button class="card-action-btn" data-session-id="${session.id}">
            ${session.id === activeSessionId ? 'In Chat' : 'Join Chat'}
          </button>
        </div>
      `;

      card.addEventListener('click', (e) => {
        if (!e.target.classList.contains('card-action-btn')) {
          joinSession(session.id);
        }
      });

      const btn = card.querySelector('.card-action-btn');
      if (btn) {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          joinSession(session.id);
        });
      }

      queueContainer.appendChild(card);
    });
  }

  // ========================================================
  // 2. Joining & Connecting to Session via Dynamic WebSocket
  // ========================================================
  function joinSession(sessionId) {
    if (activeSessionId === sessionId && counselorSocket && counselorSocket.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    // Disconnect any existing session
    if (counselorSocket) {
      try {
        counselorSocket.close();
      } catch (e) {
        console.warn('Socket close exception:', e);
      }
    }

    activeSessionId = sessionId;

    // Ensure session exists in local queue
    let existing = activeSessionsQueue.find((s) => s.id === sessionId);
    if (!existing) {
      existing = {
        id: sessionId,
        status: 'LIVE_COUNSELOR',
        timestamp: new Date(),
        preview: 'Connected by Counselor ID lookup.',
        riskTier: 2
      };
      activeSessionsQueue.unshift(existing);
    } else {
      existing.status = 'LIVE_COUNSELOR';
    }

    renderQueue();
    showActiveChatView(sessionId);

    // Dynamic WebSocket Connection (Protocol and Host agnostic)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/counselor/${sessionId}`;

    updateStatusBeacon('connecting', 'Connecting to Session...');

    try {
      counselorSocket = new WebSocket(wsUrl);

      counselorSocket.onopen = () => {
        console.log(`[Mind-Mate Counselor] Connected to ${wsUrl}`);
        updateStatusBeacon('live', 'Counselor Live');
        appendAuditNotice(`Connected securely to Student Session #${sessionId}. All student data scrubbed.`);
      };

      counselorSocket.onmessage = (event) => {
        handleCounselorIncoming(event.data);
      };

      counselorSocket.onerror = (err) => {
        console.error('[Mind-Mate Counselor] WebSocket Error:', err);
      };

      counselorSocket.onclose = (event) => {
        console.warn(`[Mind-Mate Counselor] Disconnected. Code: ${event.code}`);
        updateStatusBeacon('awaiting', 'Session Disconnected');

        if (event.code === 1008) {
          appendAuditNotice(`Server closed connection: Session #${sessionId} does not exist in database.`);
        }
      };
    } catch (e) {
      console.error('[Mind-Mate Counselor] Socket connection failed:', e);
      updateStatusBeacon('critical', 'Connection Error');
    }
  }

  function showActiveChatView(sessionId) {
    if (emptyStateView) emptyStateView.style.display = 'none';
    if (activeChatView) activeChatView.style.display = 'flex';

    if (activeSessionTitle) {
      activeSessionTitle.textContent = `Student Session #${sessionId}`;
    }

    // Clear chat stream for new session view
    chatStream.innerHTML = '';
    appendAuditNotice(`PII Scrubber Enabled: Real-time anonymization masking active on this session.`);
    counselorInput.focus();
  }

  // ========================================================
  // 3. Message Handling & PII Scrubbing Display
  // ========================================================
  function handleCounselorIncoming(rawData) {
    try {
      const data = JSON.parse(rawData);

      // Backend sends:
      // 1. Scrubbed student message: {"sender": "STUDENT", "content": scrubbed_text}
      // 2. Risk alert notification: {"event": "NEW_MODERATE_RISK"}
      // 3. System message: {"sender": "SYSTEM", "content": "..."}

      if (data.event === 'NEW_MODERATE_RISK') {
        appendAuditNotice('⚠️ New Moderate Risk Alert: Student escalated to Human Counselor.');
        // Update session in queue
        const target = activeSessionsQueue.find((s) => s.id === activeSessionId);
        if (target) {
          target.status = 'AWAITING_COUNSELOR';
          renderQueue();
        }
      } else if (data.sender === 'STUDENT') {
        appendStudentMessage(data.content);
        // Update card preview in queue
        const target = activeSessionsQueue.find((s) => s.id === activeSessionId);
        if (target) {
          target.preview = data.content;
          renderQueue();
        }
      } else if (data.sender === 'SYSTEM') {
        appendAuditNotice(data.content);
      } else {
        appendStudentMessage(data.content || rawData);
      }
    } catch (e) {
      appendStudentMessage(rawData);
    }
  }

  function appendStudentMessage(scrubbedContent) {
    const row = document.createElement('div');
    row.className = 'message-row student';

    const timeStr = getCurrentTime();
    // Highlight scrubbed tokens like [PERSON], [HOSTEL_BLOCK], [PHONE], etc.
    const highlightedContent = highlightScrubbedTokens(scrubbedContent);

    row.innerHTML = `
      <div class="message-avatar student" title="Anonymous Student">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      </div>
      <div class="message-bubble-wrapper">
        <div class="message-sender-name">
          Student (Sanitized Stream)
        </div>
        <div class="message-bubble" style="background: rgba(30, 41, 59, 0.85); border: 1px solid var(--border-subtle); color: #f8fafc; border-bottom-left-radius: 4px;">
          ${highlightedContent}
        </div>
        <div class="message-timestamp">${timeStr}</div>
      </div>
    `;

    chatStream.appendChild(row);
    scrollChatBottom();
  }

  function appendCounselorMessage(content) {
    const row = document.createElement('div');
    row.className = 'message-row counselor';
    row.style.justifyContent = 'flex-end';

    const timeStr = getCurrentTime();

    row.innerHTML = `
      <div class="message-bubble-wrapper" style="align-items: flex-end;">
        <div class="message-sender-name">You (Staff Counselor)</div>
        <div class="message-bubble" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); color: #ffffff; border-bottom-right-radius: 4px; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.25);">
          ${escapeHtml(content).replace(/\n/g, '<br/>')}
        </div>
        <div class="message-timestamp">${timeStr}</div>
      </div>
      <div class="message-avatar counselor" style="background: rgba(139, 92, 246, 0.3); border: 1px solid rgba(139, 92, 246, 0.5); color: #c084fc;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
          <path d="M12 11v6"></path>
          <path d="M9 14h6"></path>
        </svg>
      </div>
    `;

    chatStream.appendChild(row);
    scrollChatBottom();
  }

  function appendAuditNotice(text) {
    const banner = document.createElement('div');
    banner.className = 'audit-notice-banner';
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="16" x2="12" y2="12"></line>
        <line x1="12" y1="8" x2="12.01" y2="8"></line>
      </svg>
      <span>${escapeHtml(text)}</span>
    `;
    chatStream.appendChild(banner);
    scrollChatBottom();
  }

  function sendCounselorMessage() {
    if (!activeSessionId) return;

    const messageText = counselorInput.value.trim();
    if (!messageText) return;

    if (!counselorSocket || counselorSocket.readyState !== WebSocket.OPEN) {
      appendAuditNotice('Cannot send: WebSocket is not connected. Re-joining session...');
      joinSession(activeSessionId);
      return;
    }

    // Render locally
    appendCounselorMessage(messageText);

    // Send raw text to backend WebSocket endpoint
    counselorSocket.send(messageText);

    counselorInput.value = '';
    counselorInput.style.height = 'auto';
    counselorInput.focus();
  }

  // ========================================================
  // 4. THE SOS "BREAK-GLASS" BUTTON & EMERGENCY DISPATCH LOGIC
  // ========================================================
  async function executeSosUnmask(sessionId) {
    try {
      updateStatusBeacon('critical', 'Dispatching SOS...');

      // Dynamic relative path fetch (No hardcoded IP or localhost!)
      const response = await fetch(`/api/v1/hitl/sos/unmask/${sessionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errDetail = await response.text();
        throw new Error(`Server returned ${response.status}: ${errDetail}`);
      }

      const data = await response.json();
      console.log('[Mind-Mate SOS] Unmasked Emergency Data:', data);

      // Populate Modal Fields
      sosStudentName.textContent = data.student_name || 'Unknown Student';
      sosRegNo.textContent = data.reg_no || 'N/A';
      sosLocation.textContent = data.location || 'Location Not Registered';
      sosPhone.textContent = data.phone || 'N/A';

      if (sosCallLink && data.phone) {
        sosCallLink.href = `tel:${data.phone}`;
      }

      // Show the Modal
      if (sosModal) {
        sosModal.classList.add('active');
      }

      // Update Session Status to CRITICAL_SOS
      const current = activeSessionsQueue.find((s) => s.id === sessionId);
      if (current) {
        current.status = 'CRITICAL_SOS';
        renderQueue();
      }

      appendAuditNotice('🚨 EMERGENCY DISPATCH INITIATED: Student record unmasked for Campus Security.');
    } catch (err) {
      console.error('[Mind-Mate SOS] Unmasking failed:', err);
      alert(`Emergency Unmasking Error: ${err.message}\n\nPlease contact campus dispatch desk manually.`);
      updateStatusBeacon('critical', 'SOS Call Failed');
    }
  }

  // ========================================================
  // 5. Utility Helpers
  // ========================================================
  function highlightScrubbedTokens(text) {
    const escaped = escapeHtml(text);
    // Matches patterns like [HOSTEL_BLOCK], [PERSON], [PHONE], [ROOM], [REDACTED], etc.
    return escaped.replace(/\[([A-Z0-9_]+)\]/g, '<span class="scrubbed-pill">[$1]</span>');
  }

  function updateStatusBeacon(state, label) {
    if (!activeStatusBeacon || !activeStatusText) return;

    activeStatusBeacon.className = 'status-beacon';
    if (state === 'live') {
      activeStatusBeacon.classList.add('live');
    } else if (state === 'awaiting') {
      activeStatusBeacon.classList.add('awaiting');
    } else {
      activeStatusBeacon.classList.add('critical');
    }

    activeStatusText.textContent = label;
  }

  function scrollChatBottom() {
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatElapsed(date) {
    const diffSec = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    const mins = Math.floor(diffSec / 60);
    return `${mins}m ago`;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
})();
