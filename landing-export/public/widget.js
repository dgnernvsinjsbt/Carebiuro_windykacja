(function () {
  'use strict';

  // Configuration
  const API_URL = window.CHATBOT_API_URL || window.location.origin + '/api/chat';
  const PRIMARY_COLOR = '#0F2645'; // Navy blue
  const ACCENT_COLOR = '#C6A468'; // Gold

  // State
  let conversationHistory = [];
  let isOpen = false;
  let isSending = false;

  // Create styles
  function injectStyles() {
    const styles = `
      @keyframes pulse {
        0% {
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(198, 164, 104, 0.7);
        }
        70% {
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 15px rgba(198, 164, 104, 0);
        }
        100% {
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(198, 164, 104, 0);
        }
      }

      .chatbot-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: ${PRIMARY_COLOR};
        color: white;
        border: 4px solid ${ACCENT_COLOR};
        cursor: pointer;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 9998;
        transition: transform 0.2s;
        padding: 12px;
        animation: pulse 2s infinite;
      }

      .chatbot-button:hover {
        transform: scale(1.05);
        animation: none;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
      }

      .chatbot-button:active {
        transform: scale(0.95);
      }

      .chatbot-button-icon {
        position: relative;
        width: 50px;
        height: 40px;
        margin-bottom: 4px;
      }

      .chatbot-bubble-white {
        position: absolute;
        top: 0;
        left: 0;
        width: 36px;
        height: 32px;
        background: white;
        border-radius: 16px 16px 4px 16px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .chatbot-bubble-gold {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 28px;
        height: 24px;
        background: ${ACCENT_COLOR};
        border-radius: 12px 12px 12px 4px;
      }

      .chatbot-shield {
        width: 18px;
        height: 18px;
        fill: ${PRIMARY_COLOR};
      }

      .chatbot-button-text {
        font-size: 11px;
        font-weight: 700;
        text-align: center;
        line-height: 1.3;
        font-style: normal;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        letter-spacing: 0.3px;
      }

      .chatbot-window {
        position: fixed;
        bottom: 150px;
        right: 20px;
        width: 550px;
        height: 750px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
        display: flex;
        flex-direction: column;
        z-index: 9999;
        opacity: 0;
        transform: translateY(20px);
        pointer-events: none;
        transition: opacity 0.3s, transform 0.3s;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      }

      .chatbot-window.open {
        opacity: 1;
        transform: translateY(0);
        pointer-events: all;
      }

      .chatbot-header {
        background: ${PRIMARY_COLOR};
        color: white;
        padding: 20px 24px;
        border-radius: 16px 16px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .chatbot-header h3 {
        margin: 0;
        font-size: 22px;
        font-weight: 600;
      }

      .chatbot-close {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background 0.2s;
      }

      .chatbot-close:hover {
        background: rgba(255, 255, 255, 0.1);
      }

      .chatbot-messages {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
        background: #f9fafb;
      }

      .chatbot-message {
        max-width: 85%;
        padding: 14px 18px;
        border-radius: 14px;
        line-height: 1.6;
        font-size: 16px;
        animation: slideIn 0.3s ease-out;
      }

      @keyframes slideIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .chatbot-message.user {
        align-self: flex-end;
        background: ${PRIMARY_COLOR};
        color: white;
        border-bottom-right-radius: 4px;
      }

      .chatbot-message.assistant {
        align-self: flex-start;
        background: white;
        color: #000000;
        border: 1px solid #e5e7eb;
        border-bottom-left-radius: 4px;
      }

      .chatbot-typing {
        align-self: flex-start;
        background: white;
        border: 1px solid #e5e7eb;
        padding: 10px 14px;
        border-radius: 12px;
        display: flex;
        gap: 4px;
        max-width: 60px;
      }

      .chatbot-typing span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #9ca3af;
        animation: typing 1.4s infinite;
      }

      .chatbot-typing span:nth-child(2) {
        animation-delay: 0.2s;
      }

      .chatbot-typing span:nth-child(3) {
        animation-delay: 0.4s;
      }

      @keyframes typing {
        0%, 60%, 100% {
          transform: translateY(0);
          opacity: 0.7;
        }
        30% {
          transform: translateY(-10px);
          opacity: 1;
        }
      }

      .chatbot-input-area {
        padding: 20px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        gap: 12px;
        background: white;
        border-radius: 0 0 16px 16px;
      }

      .chatbot-input {
        flex: 1;
        padding: 14px 18px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        font-size: 16px;
        color: #000000;
        outline: none;
        transition: border-color 0.2s;
        font-family: inherit;
      }

      .chatbot-input:focus {
        border-color: ${PRIMARY_COLOR};
      }

      .chatbot-input:disabled {
        background: #f3f4f6;
        cursor: not-allowed;
      }

      .chatbot-send {
        padding: 14px 24px;
        background: ${PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        font-weight: 600;
        font-size: 16px;
        transition: background 0.2s;
      }

      .chatbot-send:hover:not(:disabled) {
        background: #1e40af;
      }

      .chatbot-send:disabled {
        background: #9ca3af;
        cursor: not-allowed;
      }

      .chatbot-error {
        background: #fee2e2;
        border: 1px solid #fca5a5;
        color: #991b1b;
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 14px;
        align-self: center;
        text-align: center;
      }

      /* Mobile styles */
      @media (max-width: 768px) {
        .chatbot-window {
          bottom: 0;
          right: 0;
          left: 0;
          top: 0;
          width: 100%;
          height: 100%;
          border-radius: 0;
        }

        .chatbot-header {
          border-radius: 0;
        }

        .chatbot-input-area {
          border-radius: 0;
        }

        .chatbot-button {
          bottom: 15px;
          right: 15px;
          width: 100px;
          height: 100px;
        }

        .chatbot-button-icon {
          width: 42px;
          height: 34px;
        }

        .chatbot-bubble-white {
          width: 30px;
          height: 26px;
          border-radius: 13px 13px 3px 13px;
        }

        .chatbot-bubble-gold {
          width: 22px;
          height: 18px;
          border-radius: 9px 9px 9px 3px;
        }

        .chatbot-shield {
          width: 14px;
          height: 14px;
        }

        .chatbot-button-text {
          font-size: 9px;
        }
      }
    `;

    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
  }

  // Create chatbot button
  function createButton() {
    const button = document.createElement('button');
    button.className = 'chatbot-button';
    button.setAttribute('aria-label', 'Otwórz czat');

    // Icon container with two bubbles
    const iconContainer = document.createElement('div');
    iconContainer.className = 'chatbot-button-icon';

    // White bubble with shield
    const whiteBubble = document.createElement('div');
    whiteBubble.className = 'chatbot-bubble-white';
    whiteBubble.innerHTML = `
      <svg class="chatbot-shield" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 6c1.1 0 2 .9 2 2v2h1c.55 0 1 .45 1 1v4c0 .55-.45 1-1 1h-6c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h1V9c0-1.1.9-2 2-2zm0 1c-.55 0-1 .45-1 1v2h2V9c0-.55-.45-1-1-1z"/>
      </svg>
    `;
    iconContainer.appendChild(whiteBubble);

    // Gold bubble
    const goldBubble = document.createElement('div');
    goldBubble.className = 'chatbot-bubble-gold';
    iconContainer.appendChild(goldBubble);

    button.appendChild(iconContainer);

    // Text
    const text = document.createElement('span');
    text.className = 'chatbot-button-text';
    text.innerHTML = 'Czat z<br>konsultantem';
    button.appendChild(text);

    button.addEventListener('click', toggleChat);

    return button;
  }

  // Create chatbot window
  function createWindow() {
    const window = document.createElement('div');
    window.className = 'chatbot-window';

    // Header
    const header = document.createElement('div');
    header.className = 'chatbot-header';
    header.innerHTML = `
      <h3>Czat z konsultantem</h3>
      <button class="chatbot-close" aria-label="Zamknij czat">×</button>
    `;
    window.appendChild(header);

    // Messages area
    const messages = document.createElement('div');
    messages.className = 'chatbot-messages';
    messages.id = 'chatbot-messages';

    // Welcome message
    const welcomeMsg = document.createElement('div');
    welcomeMsg.className = 'chatbot-message assistant';
    welcomeMsg.textContent = 'Cześć! W czym mogę Ci pomóc? Pytaj o Gewerbe, ubezpieczenia, legalną pracę w Niemczech.';
    messages.appendChild(welcomeMsg);

    window.appendChild(messages);

    // Input area
    const inputArea = document.createElement('div');
    inputArea.className = 'chatbot-input-area';
    inputArea.innerHTML = `
      <input
        type="text"
        class="chatbot-input"
        id="chatbot-input"
        placeholder="Wpisz swoją wiadomość..."
        maxlength="500"
      />
      <button class="chatbot-send" id="chatbot-send">Wyślij</button>
    `;
    window.appendChild(inputArea);

    // Event listeners
    header.querySelector('.chatbot-close').addEventListener('click', toggleChat);
    inputArea.querySelector('#chatbot-send').addEventListener('click', sendMessage);
    inputArea.querySelector('#chatbot-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    return window;
  }

  // Toggle chat window
  function toggleChat() {
    isOpen = !isOpen;
    const window = document.querySelector('.chatbot-window');

    if (isOpen) {
      window.classList.add('open');
      document.querySelector('#chatbot-input').focus();
    } else {
      window.classList.remove('open');
    }
  }

  // Add message to chat
  function addMessage(content, role) {
    const messagesDiv = document.getElementById('chatbot-messages');
    const message = document.createElement('div');
    message.className = `chatbot-message ${role}`;
    message.textContent = content;
    messagesDiv.appendChild(message);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Show typing indicator
  function showTyping() {
    const messagesDiv = document.getElementById('chatbot-messages');
    const typing = document.createElement('div');
    typing.className = 'chatbot-typing';
    typing.id = 'chatbot-typing';
    typing.innerHTML = '<span></span><span></span><span></span>';
    messagesDiv.appendChild(typing);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Hide typing indicator
  function hideTyping() {
    const typing = document.getElementById('chatbot-typing');
    if (typing) {
      typing.remove();
    }
  }

  // Show error message
  function showError(message) {
    const messagesDiv = document.getElementById('chatbot-messages');
    const error = document.createElement('div');
    error.className = 'chatbot-error';
    error.textContent = message || 'Przepraszamy, wystąpił błąd. Spróbuj ponownie.';
    messagesDiv.appendChild(error);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Send message
  async function sendMessage() {
    if (isSending) return;

    const input = document.getElementById('chatbot-input');
    const sendBtn = document.getElementById('chatbot-send');
    const message = input.value.trim();

    if (!message) return;

    // Disable input
    isSending = true;
    input.disabled = true;
    sendBtn.disabled = true;

    // Add user message
    addMessage(message, 'user');
    conversationHistory.push({ role: 'user', content: message });
    input.value = '';

    // Show typing indicator
    showTyping();

    // Add natural delay (1.5-2.5 seconds) to simulate typing
    const typingDelay = 1500 + Math.random() * 1000;
    await new Promise(resolve => setTimeout(resolve, typingDelay));

    try {
      // Call API
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          conversationHistory: conversationHistory.slice(-10), // Keep last 10 messages
        }),
      });

      hideTyping();

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';

      // Create message element for streaming
      const messagesDiv = document.getElementById('chatbot-messages');
      const messageElement = document.createElement('div');
      messageElement.className = 'chatbot-message assistant';
      messagesDiv.appendChild(messageElement);

      // Read stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        assistantMessage += chunk;
        messageElement.textContent = assistantMessage;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }

      // Save to history
      conversationHistory.push({ role: 'assistant', content: assistantMessage });
    } catch (error) {
      console.error('Chat error:', error);
      hideTyping();
      showError();
    } finally {
      // Re-enable input
      isSending = false;
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // Initialize chatbot
  function init() {
    // Inject styles
    injectStyles();

    // Create and append button
    const button = createButton();
    document.body.appendChild(button);

    // Create and append window
    const window = createWindow();
    document.body.appendChild(window);

    console.log('[Chatbot Widget] Initialized successfully');
  }

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
