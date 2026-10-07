/**
 * Mind-Mate Landing Page Controller
 * Secure Session Generation & Navigation
 */

(function () {
  'use strict';

  const startChatBtn = document.getElementById('startChatBtn');
  const sessionModal = document.getElementById('sessionModal');
  const manualSessionInput = document.getElementById('manualSessionInput');
  const manualConnectBtn = document.getElementById('manualConnectBtn');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const modalStatusMsg = document.getElementById('modalStatusMsg');

  if (startChatBtn) {
    startChatBtn.addEventListener('click', async () => {
      startChatBtn.disabled = true;
      startChatBtn.innerHTML = `
        <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
        </svg>
        Creating Secure Session...
      `;

      try {
        // Attempt REST call to backend session generation endpoint (Relative path, no hardcoded host!)
        const response = await fetch('/api/v1/sessions/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          const sessionId = data.session_id || data.id;
          if (sessionId) {
            window.location.href = `student_chat.html?session_id=${encodeURIComponent(sessionId)}`;
            return;
          }
        }
        
        // If endpoint is not yet mounted on backend dev branch, open the manual session picker modal
        showSessionPicker('Session server endpoint not yet mounted. Please enter an active database session ID (e.g. 1):');
      } catch (err) {
        console.warn('[Mind-Mate] Session start endpoint check:', err);
        showSessionPicker('Unable to reach automated session generator. Please enter your authorized session ID:');
      } finally {
        startChatBtn.disabled = false;
        startChatBtn.innerHTML = `
          <span>Start Anonymous Chat</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        `;
      }
    });
  }

  function showSessionPicker(message) {
    if (modalStatusMsg) {
      modalStatusMsg.textContent = message;
    }
    if (sessionModal) {
      sessionModal.classList.add('active');
    }
    if (manualSessionInput) {
      manualSessionInput.focus();
    }
  }

  if (manualConnectBtn && manualSessionInput) {
    manualConnectBtn.addEventListener('click', () => {
      const enteredId = manualSessionInput.value.trim();
      if (enteredId) {
        window.location.href = `student_chat.html?session_id=${encodeURIComponent(enteredId)}`;
      }
    });

    manualSessionInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        manualConnectBtn.click();
      }
    });
  }

  if (closeModalBtn && sessionModal) {
    closeModalBtn.addEventListener('click', () => {
      sessionModal.classList.remove('active');
    });
  }
})();
