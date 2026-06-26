/* ==========================================================
   AI Guard Demo — frontend logic
   Vanilla JS. No framework. ~150 LOC.
   ========================================================== */

(() => {
    'use strict';

    // ---------- state ----------
    const state = {
        sessionId: null,
        guardOn:   false,
        sending:   false,
    };

    // ---------- DOM ----------
    const $ = sel => document.querySelector(sel);
    const stream      = $('#chat-stream');
    const input       = $('#user-input');
    const form        = $('#composer');
    const sendBtn     = $('#send-btn');
    const guardToggle = $('#guard-toggle');
    const statusPill  = $('#status-pill');
    const guardModeEl = $('#guard-mode');
    const sessionEl   = $('#session-id-short');
    const toggleHint  = $('#toggle-hint');
    const clearBtn    = $('#clear-chat');

    // ---------- init ----------
    init();

    async function init() {
        try {
            const r = await fetch('/session/create', { method: 'POST' });
            const data = await r.json();
            state.sessionId = data.session_id;
            sessionEl.textContent = state.sessionId.slice(0, 8);
            await pollHealth();
        } catch (e) {
            renderSystem(`No pude conectar con el backend: ${e.message}`);
        }
        bind();
    }

    async function pollHealth() {
        try {
            const h = await (await fetch('/health')).json();
            guardModeEl.textContent = h.guard_mode;
        } catch (_) { /* ignore */ }
    }

    function bind() {
        form.addEventListener('submit', onSubmit);
        guardToggle.addEventListener('change', onToggleGuard);
        clearBtn.addEventListener('click', onClearChat);
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.dataset.prompt;
                input.focus();
            });
        });
    }

    // ---------- events ----------
    async function onToggleGuard(e) {
        const enabled = e.target.checked;
        try {
            const r = await fetch('/session/guard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: state.sessionId, enabled }),
            });
            const data = await r.json();
            state.guardOn = !!data.ai_guard_enabled;
            updateGuardUI();
        } catch (err) {
            renderSystem(`Error al cambiar AI Guard: ${err.message}`);
            e.target.checked = state.guardOn;
        }
    }

    function updateGuardUI() {
        document.body.dataset.guard = state.guardOn ? 'on' : 'off';
        statusPill.textContent = state.guardOn ? 'ON' : 'OFF';
        statusPill.classList.toggle('status-on',  state.guardOn);
        statusPill.classList.toggle('status-off', !state.guardOn);
        toggleHint.textContent = state.guardOn
            ? 'Trend Micro AI Guard valida cada input y output. Los ataques son bloqueados antes de llegar al modelo o al usuario.'
            : 'El modelo está expuesto. Los prompts maliciosos llegan al LLM y los datos sensibles pueden filtrarse.';
    }

    function onClearChat() {
        stream.innerHTML = '';
        renderSystem(
            state.guardOn
                ? 'Chat reiniciado. AI Guard <b>ON</b>: el modelo está protegido.'
                : 'Chat reiniciado. AI Guard <b>OFF</b>: el modelo es vulnerable.'
        );
    }

    async function onSubmit(e) {
        e.preventDefault();
        const msg = input.value.trim();
        if (!msg || state.sending) return;

        state.sending = true;
        sendBtn.disabled = true;
        input.value = '';

        renderUser(msg);
        const typingNode = renderTyping();

        try {
            const r = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    session_id: state.sessionId,
                }),
            });
            const data = await r.json();
            typingNode.remove();
            renderBot(data);
        } catch (err) {
            typingNode.remove();
            renderSystem(`Error en la solicitud: ${err.message}`);
        } finally {
            state.sending = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // ---------- rendering ----------
    function renderUser(text) {
        const node = document.createElement('div');
        node.className = 'msg msg-user';
        node.innerHTML = `
            <div class="msg-meta">USER</div>
            <div class="msg-body"></div>`;
        node.querySelector('.msg-body').textContent = text;
        stream.appendChild(node);
        scrollEnd();
    }

    function renderTyping() {
        const node = document.createElement('div');
        node.className = 'msg msg-bot';
        node.innerHTML = `
            <div class="msg-meta">CHATBOT</div>
            <div class="msg-body"><span class="typing">procesando</span></div>`;
        stream.appendChild(node);
        scrollEnd();
        return node;
    }

    function renderBot(data) {
        const cls = ['msg', 'msg-bot'];
        const badges = [];

        if (data.blocked) {
            cls.push('bot-blocked');
            badges.push(`<span class="badge badge-blocked">AI GUARD · BLOCK</span>`);
            if (data.stage) badges.push(`<span class="badge badge-stage">stage: ${data.stage}</span>`);
        } else if (!data.ai_guard_enabled && data.attack_patterns_detected.length) {
            cls.push('bot-vulnerable');
            badges.push(`<span class="badge badge-vuln">MODEL · COMPROMISED</span>`);
            badges.push(`<span class="badge badge-stage">attack patterns: ${data.attack_patterns_detected.length}</span>`);
        }
        badges.push(`<span class="badge badge-mode">guard: ${data.guard_mode}</span>`);

        const reasons = (data.guard_reasons && data.guard_reasons.length)
            ? `<div class="reasons">
                 <div class="reasons-title">AI Guard reasons</div>
                 ${escapeHtml(data.guard_reasons.slice(0, 5).join('\n'))}
               </div>`
            : '';

        const node = document.createElement('div');
        node.className = cls.join(' ');
        node.innerHTML = `
            <div class="msg-meta">CHATBOT</div>
            <div class="msg-body"></div>
            <div class="badge-row">${badges.join('')}</div>
            ${reasons}`;
        node.querySelector('.msg-body').textContent = data.response;
        stream.appendChild(node);
        scrollEnd();
    }

    function renderSystem(html) {
        const node = document.createElement('div');
        node.className = 'msg msg-system';
        node.innerHTML = `
            <div class="msg-meta">SYSTEM</div>
            <div class="msg-body">${html}</div>`;
        stream.appendChild(node);
        scrollEnd();
    }

    function scrollEnd() {
        stream.scrollTop = stream.scrollHeight;
    }

    function escapeHtml(s) {
        return s.replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;',
            '"': '&quot;', "'": '&#39;'
        }[c]));
    }
})();
