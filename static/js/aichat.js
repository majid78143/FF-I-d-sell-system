/* aichat.js — AI Chat page logic */

const chatMessages = document.getElementById('chatMessages');
const chatInput    = document.getElementById('chatInput');
const chatSend     = document.getElementById('chatSend');

if (!chatMessages || !chatInput || !chatSend) {
  // AI disabled or not on this page
} else {

  // Auto-resize input
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
  });

  // Send on Enter (Shift+Enter = newline)
  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  chatSend.addEventListener('click', sendMessage);

  // Suggested questions
  document.querySelectorAll('.suggested-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      chatInput.value = btn.dataset.q || btn.textContent.trim();
      sendMessage();
    });
  });

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage('user', text);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    chatSend.disabled = true;

    const loadingId = appendLoading();

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      removeLoading(loadingId);

      if (data.error) {
        appendMessage('bot', `Error: ${data.error}`, true);
      } else {
        appendMessage('bot', data.reply || 'No response received.');
      }
    } catch (err) {
      removeLoading(loadingId);
      appendMessage('bot', 'Connection error. Please try again.', true);
    } finally {
      chatSend.disabled = false;
      chatInput.focus();
    }
  }

  function appendMessage(role, text, isError = false) {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar';

    if (role === 'bot') {
      avatar.className += ' bot-avatar';
      avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 10h8M8 14h5"/></svg>`;
    } else {
      avatar.className += ' user-avatar';
      avatar.textContent = 'U';
    }

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    if (isError) bubble.style.cssText = 'background:#fef2f2;color:#991b1b;border-color:#fca5a5';
    bubble.innerHTML = formatMessage(text);

    div.appendChild(avatar);
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function appendLoading() {
    const id = 'loading_' + Date.now();
    const div = document.createElement('div');
    div.className = 'chat-msg bot chat-loading';
    div.id = id;
    div.innerHTML = `
      <div class="chat-avatar bot-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 10h8M8 14h5"/></svg>
      </div>
      <div class="chat-bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>`;
    chatMessages.appendChild(div);
    scrollToBottom();
    return id;
  }

  function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function formatMessage(text) {
    // Basic markdown-like formatting
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code style="background:#f3f4f6;padding:.1rem .3rem;border-radius:3px;font-family:monospace">$1</code>')
      .replace(/\n/g, '<br>');
  }

}
