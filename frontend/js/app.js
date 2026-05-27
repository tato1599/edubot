/**
 * EduBot Frontend v3.0 - Tema Sith Limpio
 * Input estilo Gemini + Chat con streaming
 */

const API_BASE = (window.location.protocol === 'file:') 
    ? 'http://localhost:8000' 
    : '';  // Rutas relativas cuando se sirve desde nginx/fastapi

const API_PREFIX = '/api';  // Prefijo para endpoints API

// ── Referencias DOM ──
const welcomeScreen = document.getElementById('welcome-screen');
const chatScreen = document.getElementById('chat-screen');
const welcomeInput = document.getElementById('welcome-input');
const welcomeSend = document.getElementById('welcome-send');
const backBtn = document.getElementById('back-btn');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const globalLoader = document.getElementById('global-loader');

let isWaiting = false;
let conversationHistory = [];

// ── Inicialización ──
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    
    // Auto-focus en input de bienvenida
    if (welcomeInput) {
        setTimeout(() => welcomeInput.focus(), 100);
    }
    
    checkBackend();
});

function setupEventListeners() {
    // Input de bienvenida
    if (welcomeInput) {
        welcomeInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                startChat(welcomeInput.value.trim());
            }
        });
        
        welcomeInput.addEventListener('input', () => {
            welcomeInput.style.height = 'auto';
            welcomeInput.style.height = welcomeInput.scrollHeight + 'px';
        });
    }
    
    if (welcomeSend) {
        welcomeSend.addEventListener('click', () => {
            startChat(welcomeInput.value.trim());
        });
    }
    
    // Chips de sugerencia
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            startChat(chip.dataset.text);
        });
    });
    
    // Chat
    if (backBtn) {
        backBtn.addEventListener('click', goToWelcome);
    }
    
    if (sendBtn) {
        sendBtn.addEventListener('click', handleSend);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });
        
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = messageInput.scrollHeight + 'px';
        });
    }
}

// ── Transición Welcome -> Chat ──
function startChat(firstMessage) {
    if (!firstMessage) {
        welcomeInput?.focus();
        return;
    }
    
    // Transición de pantallas
    welcomeScreen.classList.add('fade-out');
    
    setTimeout(() => {
        welcomeScreen.classList.add('hidden');
        welcomeScreen.classList.remove('fade-out');
        
        chatScreen.classList.remove('hidden');
        // Trigger reflow para que la transición CSS se active
        void chatScreen.offsetWidth;
        chatScreen.classList.add('active');
        
        // Enviar mensaje inicial
        conversationHistory.push({ role: "user", content: firstMessage });
        updateMemoryIndicator();
        
        addUserMessage(firstMessage);
        welcomeInput.value = '';
        welcomeInput.style.height = 'auto';
        
        const easterEgg = checkSithEasterEgg(firstMessage);
        if (easterEgg) {
            showTyping();
            setTimeout(() => {
                addBotMessage(easterEgg);
                conversationHistory.push({ role: "assistant", content: easterEgg });
                trimHistory();
                updateMemoryIndicator();
            }, 700);
        } else {
            showTyping();
            sendToAPI(firstMessage);
        }
    }, 350);
}

function goToWelcome() {
    chatScreen.classList.remove('active');
    
    setTimeout(() => {
        chatScreen.classList.add('hidden');
        chatMessages.innerHTML = '';
        conversationHistory = [];
        updateMemoryIndicator();
        
        welcomeScreen.classList.remove('hidden');
        welcomeInput.value = '';
        welcomeInput.style.height = 'auto';
        setTimeout(() => welcomeInput.focus(), 100);
    }, 300);
}

// ── Easter Eggs Sith ──
const SITH_EASTER_EGGS = {
    'lado oscuro': 'El lado oscuro es un camino a muchas habilidades que algunos consideran... antinaturales. Pero en el TecNM ITCJ, prefiero el lado del conocimiento. ¿En qué puedo ayudarte?',
    'sith': 'Los Sith se rigen por la Regla de Dos: un maestro y un aprendiz. En el TecNM, nosotros nos regimos por la Regla del Estudiante: ¡estudia mucho y aprueba tus materias!',
    'force': 'Que la Fuerza te acompañe... y también tus estudios. ¿Necesitas ayuda con algo del TecNM ITCJ?',
    'sable': 'Un sable láser rojo requiere cristales sintéticos del lado oscuro. Aquí en el Tec usamos conocimiento real, no sintético. ¿Qué información buscas?',
    'darth': 'Darth Vader tenía un 96% de midiclorianos. Tú tienes un 100% de potencial estudiantil. ¡Úsalo! ¿En qué te ayudo?',
    'vader': 'Luke, yo soy tu... asistente virtual del TecNM ITCJ. ¿Necesitas algo?',
    'padawan': 'Un Padawan necesita entrenar. Un estudiante del Tec necesita... esta retícula. ¿Quieres ver tu plan de estudios?',
    'maestro': 'El maestro Yoda decía: "Hazlo o no lo hagas, pero no lo intentes". En el Tec decimos: "Estudia o no estudies, pero no lo dejes para el último día".',
    'jedi': 'Los Jedi meditan para encontrar paz. Los estudiantes del Tec... también deberían meditar antes de los exámenes. ¿Necesitas ayuda con algo?',
    'imperio': 'El Imperio Galáctico construyó la Estrella de la Muerte. El TecNM ITCJ construye... ingenieros de sistemas. Mucho más útil.',
    'rebelion': 'La Rebelión lucha contra el Imperio. Nosotros luchamos contra... las materias reprobadas y los trámites burocráticos. ¡Estoy aquí para ayudarte!',
};

function checkSithEasterEgg(text) {
    if (!text) return null;
    const lowerText = text.toLowerCase();
    for (const [key, response] of Object.entries(SITH_EASTER_EGGS)) {
        if (lowerText.includes(key)) {
            return response;
        }
    }
    return null;
}

// ── Chat Functions ──
function handleSend() {
    const text = messageInput.value.trim();
    if (!text || isWaiting) return;
    
    conversationHistory.push({ role: "user", content: text });
    updateMemoryIndicator();
    
    addUserMessage(text);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    const easterEgg = checkSithEasterEgg(text);
    if (easterEgg) {
        showTyping();
        setTimeout(() => {
            addBotMessage(easterEgg);
            conversationHistory.push({ role: "assistant", content: easterEgg });
            trimHistory();
            updateMemoryIndicator();
        }, 700);
        return;
    }
    
    showTyping();
    sendToAPI(text);
}

function addUserMessage(text) {
    const msgDiv = createMessageElement('user', text);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function addBotMessage(text, sources = []) {
    hideTyping();
    const msgDiv = createMessageElement('bot', text, sources);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function createMessageElement(type, text, sources = []) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (type === 'bot') {
        avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M12 9h.01"/><path d="M8 22h8"/></svg>`;
    } else {
        avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
    }
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const formatted = text
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    content.innerHTML = `<p>${formatted}</p>`;
    
    if (sources && sources.length > 0) {
        const pillsDiv = document.createElement('div');
        pillsDiv.style.marginTop = '0.5rem';
        pillsDiv.style.display = 'flex';
        pillsDiv.style.flexWrap = 'wrap';
        pillsDiv.style.gap = '0.4rem';
        
        sources.forEach(src => {
            const pill = document.createElement('span');
            pill.className = 'source-pill';
            pill.innerHTML = `📄 ${src.titulo} <span style="opacity:0.6">• ${src.categoria}</span>`;
            pillsDiv.appendChild(pill);
        });
        content.appendChild(pillsDiv);
    }
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    
    div.appendChild(avatar);
    div.appendChild(content);
    div.appendChild(time);
    
    return div;
}

function showTyping() {
    isWaiting = true;
    const div = document.createElement('div');
    div.className = 'message bot typing-indicator';
    div.id = 'typing-indicator';
    div.innerHTML = `
        <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                <path d="M12 9h.01"/>
                <path d="M8 22h8"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="typing">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function hideTyping() {
    isWaiting = false;
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function trimHistory() {
    if (conversationHistory.length > 10) {
        conversationHistory = conversationHistory.slice(-10);
    }
}

function updateMemoryIndicator() {
    const indicator = document.getElementById('memory-indicator');
    if (!indicator) return;
    
    const turnos = Math.floor(conversationHistory.length / 2);
    if (turnos > 0) {
        indicator.textContent = `${turnos} turno${turnos > 1 ? 's' : ''} en memoria`;
        indicator.classList.add('active');
    } else {
        indicator.textContent = 'Memoria activa';
        indicator.classList.remove('active');
    }
}

// ── API Communication (STREAMING con MEMORIA) ──
async function sendToAPI(message) {
    try {
        const response = await fetch(`${API_BASE}${API_PREFIX}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: conversationHistory })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentMessage = '';
        let currentSources = [];
        let messageElement = null;
        let contentElement = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n\n');
            buffer = lines.pop();
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.type === 'sources') {
                        currentSources = data.sources || [];
                    }
                    else if (data.type === 'token') {
                        if (!messageElement) {
                            hideTyping();
                            messageElement = createMessageElement('bot', '');
                            chatMessages.appendChild(messageElement);
                            contentElement = messageElement.querySelector('.message-content p');
                            scrollToBottom();
                        }
                        
                        currentMessage += data.text;
                        if (contentElement) {
                            contentElement.innerHTML = currentMessage
                                .replace(/\n\n/g, '</p><p>')
                                .replace(/\n/g, '<br>');
                        }
                        scrollToBottom();
                    }
                    else if (data.type === 'correction') {
                        // Reemplazar mensaje completo con version corregida en espanol
                        currentMessage = data.text;
                        if (contentElement) {
                            contentElement.innerHTML = currentMessage
                                .replace(/\n\n/g, '</p><p>')
                                .replace(/\n/g, '<br>');
                        }
                        scrollToBottom();
                    }
                    else if (data.type === 'done') {
                        if (currentMessage) {
                            conversationHistory.push({ role: "assistant", content: currentMessage });
                            trimHistory();
                            updateMemoryIndicator();
                        }
                        isWaiting = false;
                    }
                    else if (data.type === 'error') {
                        if (messageElement) {
                            const content = messageElement.querySelector('.message-content p');
                            if (content) content.innerHTML = `Error: ${data.message}`;
                        } else {
                            hideTyping();
                            addBotMessage(`Error: ${data.message}`);
                        }
                        isWaiting = false;
                    }
                    
                } catch (e) {
                    console.warn('Error parsing SSE:', e);
                }
            }
        }
        
    } catch (error) {
        console.error('Error:', error);
        hideTyping();
        addBotMessage(
            "Lo siento, hubo un error al comunicarme con el servidor.\n\n" +
            "Por favor verifica que el backend está corriendo.\n\n" +
            "Error: " + error.message
        );
        isWaiting = false;
    }
}

// ── Health check al cargar ──
async function checkBackend() {
    try {
        const res = await fetch(`${API_BASE}${API_PREFIX}/health`, { method: 'GET' });
        if (res.ok) {
            console.log('[EduBot] Backend conectado correctamente');
        }
    } catch (e) {
        console.warn('[EduBot] Backend no disponible. Inicia con: uvicorn backend.main:app --reload');
    }
}

checkBackend();

// ═══════════════════════════════════════════════════════════
// SHARE / TUNNEL PANEL
// ═══════════════════════════════════════════════════════════

const sharePanel = document.getElementById('share-panel');
const shareBtn = document.getElementById('share-btn');
const closeShareBtn = document.getElementById('close-share');
const createTunnelBtn = document.getElementById('create-tunnel-btn');
const closeTunnelBtn = document.getElementById('close-tunnel-btn');
const copyUrlBtn = document.getElementById('copy-url-btn');
const tunnelUrlInput = document.getElementById('tunnel-url');
const tunnelUrlContainer = document.getElementById('tunnel-url-container');
const tunnelStatus = document.getElementById('tunnel-status');
const tunnelLoading = document.getElementById('tunnel-loading');

let currentTunnel = null;

function setupSharePanel() {
    if (!shareBtn) return;
    
    shareBtn.addEventListener('click', () => {
        sharePanel.classList.remove('hidden');
        checkTunnelStatus();
    });
    
    closeShareBtn?.addEventListener('click', () => {
        sharePanel.classList.add('hidden');
    });
    
    // Cerrar al hacer click fuera
    sharePanel?.addEventListener('click', (e) => {
        if (e.target === sharePanel) {
            sharePanel.classList.add('hidden');
        }
    });
    
    createTunnelBtn?.addEventListener('click', createTunnel);
    closeTunnelBtn?.addEventListener('click', closeTunnel);
    copyUrlBtn?.addEventListener('click', copyTunnelUrl);
}

async function checkTunnelStatus() {
    try {
        const res = await fetch(`${API_BASE}${API_PREFIX}/tunnel/list`);
        if (!res.ok) return;
        
        const data = await res.json();
        if (data.count > 0 && data.tunnels.length > 0) {
            const tunnel = data.tunnels[0];
            currentTunnel = tunnel;
            showTunnelActive(tunnel.url);
        } else {
            showTunnelInactive();
        }
    } catch (e) {
        console.warn('[Tunnel] No se pudo verificar estado:', e);
        showTunnelInactive();
    }
}

async function createTunnel() {
    if (!createTunnelBtn || !tunnelLoading) return;
    
    createTunnelBtn.disabled = true;
    createTunnelBtn.classList.add('hidden');
    tunnelLoading.classList.remove('hidden');
    
    try {
        const res = await fetch(`${API_BASE}${API_PREFIX}/tunnel/create?provider=cloudflare`, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (data.success) {
            currentTunnel = data;
            showTunnelActive(data.url);
            
            // Copiar automaticamente al portapapeles
            if (navigator.clipboard) {
                navigator.clipboard.writeText(data.url);
                showToast('URL copiada al portapapeles');
            }
        } else {
            showTunnelError(data.error || 'Error desconocido');
        }
    } catch (e) {
        showTunnelError('Error de conexion. Verifica que el backend este corriendo.');
    } finally {
        tunnelLoading.classList.add('hidden');
    }
}

async function closeTunnel() {
    if (!currentTunnel?.tunnel_id) return;
    
    closeTunnelBtn.disabled = true;
    
    try {
        await fetch(`${API_BASE}${API_PREFIX}/tunnel/close/${currentTunnel.tunnel_id}`, {
            method: 'POST'
        });
        showTunnelInactive();
        currentTunnel = null;
    } catch (e) {
        console.error('[Tunnel] Error cerrando:', e);
    } finally {
        closeTunnelBtn.disabled = false;
    }
}

function showTunnelActive(url) {
    tunnelStatus.innerHTML = '<span class="tunnel-indicator active">Tunnel activo</span>';
    tunnelUrlContainer.classList.remove('hidden');
    tunnelUrlInput.value = url;
    createTunnelBtn.classList.add('hidden');
    closeTunnelBtn.classList.remove('hidden');
}

function showTunnelInactive() {
    tunnelStatus.innerHTML = '<span class="tunnel-indicator">No hay tunnel activo</span>';
    tunnelUrlContainer.classList.add('hidden');
    createTunnelBtn.classList.remove('hidden');
    createTunnelBtn.disabled = false;
    closeTunnelBtn.classList.add('hidden');
}

function showTunnelError(message) {
    tunnelStatus.innerHTML = `<span class="tunnel-indicator" style="color: var(--tec-red-light)">Error: ${message}</span>`;
    tunnelUrlContainer.classList.add('hidden');
    createTunnelBtn.classList.remove('hidden');
    createTunnelBtn.disabled = false;
}

function copyTunnelUrl() {
    if (!tunnelUrlInput?.value) return;
    
    tunnelUrlInput.select();
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(tunnelUrlInput.value);
    } else {
        document.execCommand('copy');
    }
    
    showToast('URL copiada al portapapeles');
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: var(--bg-light);
        border: 1px solid var(--border);
        padding: 0.75rem 1.5rem;
        border-radius: var(--radius-sm);
        font-size: 0.9rem;
        font-weight: 500;
        z-index: 300;
        animation: fadeInUp 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// Inicializar panel de compartir
document.addEventListener('DOMContentLoaded', setupSharePanel);
