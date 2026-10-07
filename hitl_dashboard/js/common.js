/**
 * Mind-Mate: Digital Mental Health Risk Screening System
 * Common Utilities & Dynamic Routing Helpers
 */

/**
 * Dynamically resolves WebSocket URL using window.location.host
 * NEVER hardcodes localhost or 127.0.0.1
 * @param {string} path - E.g. '/ws/student/1' or '/ws/counselor/1'
 * @returns {string} - Full WebSocket URL
 */
function getWebSocketUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${protocol}//${window.location.host}${cleanPath}`;
}

/**
 * Escapes HTML characters to prevent XSS attacks
 * @param {string} str - Raw text
 * @returns {string} - Safe escaped text
 */
function escapeHTML(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.innerText = str;
  return div.innerHTML;
}

/**
 * Formats scrubbed PII tags (e.g. [HOSTEL_BLOCK], [PERSON], [PHONE_NUMBER])
 * into high-visibility privacy badges
 * @param {string} text - Message text
 * @returns {string} - Sanitized HTML with highlighted PII tags
 */
function highlightPIITags(text) {
  if (!text) return '';
  const escaped = escapeHTML(text);
  // Match tokens like [HOSTEL_BLOCK], [PERSON], [PHONE_NUMBER], [ROOM], [EMAIL], [REDACTED]
  return escaped.replace(/\[([A-Z0-9_\-\s]{2,30})\]/g, (match, tokenName) => {
    return `<span class="pii-tag" title="Anonymized by Presidio PII Engine">[${tokenName}]</span>`;
  });
}

/**
 * Formats a timestamp into human-readable 12-hour format (e.g. "03:45 PM")
 * @param {Date|string|number} dateInput
 * @returns {string}
 */
function formatTime(dateInput = new Date()) {
  const date = new Date(dateInput);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Plays a pleasant synth tone using the Web Audio API
 * No external audio files needed!
 * @param {'chime'|'alert'|'sos'} type
 */
function playAudioAlert(type = 'chime') {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    if (type === 'chime') {
      // Pleasant dual tone for incoming message
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === 'alert') {
      // Moderate escalation alert
      const now = ctx.currentTime;
      [440, 659.25].forEach((freq, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + i * 0.12);
        gain.gain.setValueAtTime(0.12, now + i * 0.12);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.12 + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.12);
        osc.stop(now + i * 0.12 + 0.25);
      });
    } else if (type === 'sos') {
      // Emergency warning pulse
      const now = ctx.currentTime;
      for (let i = 0; i < 3; i++) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, now + i * 0.2);
        osc.frequency.linearRampToValueAtTime(440, now + i * 0.2 + 0.18);
        gain.gain.setValueAtTime(0.2, now + i * 0.2);
        gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.2 + 0.18);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + i * 0.2);
        osc.stop(now + i * 0.2 + 0.2);
      }
    }
  } catch (e) {
    console.debug('Audio alert skipped:', e);
  }
}

/**
 * Toast Notification Dispatcher
 * @param {string} message
 * @param {'success'|'warning'|'danger'|'info'} type
 * @param {number} duration
 */
function showToast(message, type = 'info', duration = 4000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconMap = {
    success: '✅',
    warning: '⚠️',
    danger: '🚨',
    info: 'ℹ️'
  };

  toast.innerHTML = `
    <span>${iconMap[type] || 'ℹ️'}</span>
    <span style="flex:1;">${escapeHTML(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Copies plain text to user clipboard with toast feedback
 * @param {string} text
 * @param {string} label
 */
async function copyToClipboard(text, label = 'Copied to clipboard!') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(label, 'success');
  } catch (err) {
    // Fallback
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
    showToast(label, 'success');
  }
}
