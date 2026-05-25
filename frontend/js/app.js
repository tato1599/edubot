/**
 * EduBot Frontend - Lógica de la interfaz con GSAP
 * Maneja animaciones, navegación y comunicación con la API FastAPI
 */

// Si el frontend se sirve desde el mismo dominio que el backend (ej. FastAPI sirviendo estáticos),
// usamos URL relativa. Si se abre directamente desde archivo (file://), usamos localhost.
const API_BASE = (window.location.protocol === 'file:') 
    ? 'http://localhost:8000' 
    : `${window.location.protocol}//${window.location.host}`;

// ── Referencias DOM ──
const welcomeScreen = document.getElementById('welcome-screen');
const chatScreen = document.getElementById('chat-screen');
const startBtn = document.getElementById('start-btn');
const backBtn = document.getElementById('back-btn');
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const globalLoader = document.getElementById('global-loader');
const particlesContainer = document.getElementById('particles');

let isWaiting = false;

// ── Inicialización ──
document.addEventListener('DOMContentLoaded', () => {
    initAnimations();
    generateParticles();
    setupEventListeners();
});

// ── Animaciones GSAP de entrada ──
function initAnimations() {
    // Verificar que GSAP esté disponible
    if (typeof gsap === 'undefined') {
        console.warn('[EduBot] GSAP no cargó. Usando UI sin animaciones.');
        return;
    }

    try {
        const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
        
        // Usar fromTo() para garantizar estado final visible (opacity: 1)
        // y evitar que los elementos queden atrapados en opacity: 0
        tl.fromTo('.logo-core',
            { scale: 0, rotation: 180 },
            { scale: 1, rotation: 0, duration: 1, ease: 'back.out(1.7)' }
        )
        .fromTo('.logo-ring',
            { scale: 0, opacity: 0 },
            { scale: 1, opacity: 1, stagger: 0.15, duration: 0.8 },
            '-=0.6'
        )
        .fromTo('.title-line',
            { y: 40, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.8 },
            '-=0.4'
        )
        .fromTo('.title-sub',
            { y: 20, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.6 },
            '-=0.5'
        )
        .fromTo('.welcome-desc',
            { y: 20, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.6 },
            '-=0.4'
        )
        .fromTo('.pill',
            { scale: 0.8, opacity: 0 },
            { scale: 1, opacity: 1, stagger: 0.1, duration: 0.5, ease: 'back.out(1.4)' },
            '-=0.3'
        )
        .fromTo('.start-btn',
            { y: 30, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.7, ease: 'back.out(1.2)' },
            '-=0.2'
        );
    } catch (e) {
        console.warn('[EduBot] Error en animaciones:', e);
    }
}

// ── Generador de partículas ──
function generateParticles() {
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.top = Math.random() * 100 + '%';
        p.style.animationDelay = Math.random() * 5 + 's';
        p.style.opacity = Math.random() * 0.5 + 0.1;
        const size = Math.random() * 4 + 2;
        p.style.width = size + 'px';
        p.style.height = size + 'px';
        particlesContainer.appendChild(p);
        
        // Animar con GSAP si está disponible
        if (typeof gsap !== 'undefined') {
            try {
                gsap.to(p, {
                    y: -100 - Math.random() * 200,
                    x: (Math.random() - 0.5) * 100,
                    opacity: 0,
                    duration: 5 + Math.random() * 5,
                    repeat: -1,
                    delay: Math.random() * 5,
                    ease: 'none'
                });
            } catch (e) {
                // Ignorar error de animación de partículas
            }
        }
    }
}

// ── Event Listeners ──
function setupEventListeners() {
    startBtn.addEventListener('click', goToChat);
    backBtn.addEventListener('click', goToWelcome);
    
    sendBtn.addEventListener('click', handleSend);
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });
}

// ── Navegación ──
function goToChat() {
    const switchToChat = () => {
        welcomeScreen.classList.add('hidden');
        chatScreen.classList.remove('hidden');
        chatScreen.style.opacity = '1';
        chatScreen.style.transform = 'none';
        
        // Mostrar mensaje de bienvenida del bot
        setTimeout(() => {
            addBotMessage(
                "¡Hola! Soy EduBot, tu asistente escolar.\n\n" +
                "Puedo ayudarte con:\n" +
                "• 🎓 Trámites escolares (inscripción, reinscripción, constancias, becas, titulación)\n" +
                "• 🥗 Nutrición escolar según el SMAE (menús, porciones, recomendaciones)\n\n" +
                "¿En qué puedo ayudarte hoy?"
            );
        }, 300);
    };

    // Intentar animar con GSAP, si falla hacer el cambio directo
    if (typeof gsap !== 'undefined') {
        try {
            gsap.to(welcomeScreen, {
                opacity: 0,
                scale: 0.95,
                duration: 0.5,
                ease: 'power2.in',
                onComplete: switchToChat
            });
            return;
        } catch (e) {
            console.warn('[EduBot] GSAP falló en transición, usando fallback:', e);
        }
    }
    switchToChat();
}

function goToWelcome() {
    const switchToWelcome = () => {
        chatScreen.classList.add('hidden');
        welcomeScreen.classList.remove('hidden');
        welcomeScreen.style.opacity = '1';
        welcomeScreen.style.transform = 'none';
        chatMessages.innerHTML = '';
    };

    if (typeof gsap !== 'undefined') {
        try {
            gsap.to(chatScreen, {
                opacity: 0,
                x: -50,
                duration: 0.4,
                ease: 'power2.in',
                onComplete: switchToWelcome
            });
            return;
        } catch (e) {
            console.warn('[EduBot] GSAP falló en transición, usando fallback:', e);
        }
    }
    switchToWelcome();
}

// ── Chat Functions ──
function handleSend() {
    const text = messageInput.value.trim();
    if (!text || isWaiting) return;
    
    addUserMessage(text);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    showTyping();
    sendToAPI(text);
}

function addUserMessage(text) {
    const msgDiv = createMessageElement('user', text);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    animateMessageIn(msgDiv);
}

function addBotMessage(text, sources = []) {
    hideTyping();
    const msgDiv = createMessageElement('bot', text, sources);
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    animateMessageIn(msgDiv);
}

function createMessageElement(type, text, sources = []) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (type === 'bot') {
        avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M12 9h.01"/><path d="M8 22h8"/></svg>`;
    } else {
        avatar.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;
    }
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    // Convertir saltos de línea en <br> o <p>
    const formatted = text
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
    content.innerHTML = `<p>${formatted}</p>`;
    
    // Agregar pills de fuentes si existen
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

function animateMessageIn(element) {
    element.style.opacity = '1';
    element.style.transform = 'translateY(0)';
    
    if (typeof gsap !== 'undefined') {
        try {
            gsap.to(element, {
                opacity: 1,
                y: 0,
                duration: 0.5,
                ease: 'power3.out'
            });
        } catch (e) {
            // Fallback ya aplicado arriba
        }
    }
}

function showTyping() {
    isWaiting = true;
    const div = document.createElement('div');
    div.className = 'message bot typing-indicator';
    div.id = 'typing-indicator';
    div.style.opacity = '1';
    div.style.transform = 'translateY(0)';
    div.innerHTML = `
        <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
    
    if (typeof gsap !== 'undefined') {
        try {
            gsap.to(div, { opacity: 1, y: 0, duration: 0.3 });
        } catch (e) {}
    }
}

function hideTyping() {
    isWaiting = false;
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        if (typeof gsap !== 'undefined') {
            try {
                gsap.to(indicator, {
                    opacity: 0,
                    y: -10,
                    duration: 0.3,
                    onComplete: () => indicator.remove()
                });
                return;
            } catch (e) {}
        }
        indicator.remove();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── API Communication ──
async function sendToAPI(message) {
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: [] })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        addBotMessage(data.response, data.sources);
        
    } catch (error) {
        console.error('Error:', error);
        hideTyping();
        addBotMessage(
            "Lo siento, hubo un error al comunicarme con el servidor.\n\n" +
            "Por favor verifica que:\n" +
            "1. El backend está corriendo: `python backend/main.py`\n" +
            "2. La URL de la API es correcta: " + API_BASE + "\n\n" +
            "Error: " + error.message
        );
    }
}

// ── Health check al cargar ──
async function checkBackend() {
    try {
        const res = await fetch(`${API_BASE}/`, { method: 'GET' });
        if (res.ok) {
            console.log('[EduBot] Backend conectado correctamente');
        }
    } catch (e) {
        console.warn('[EduBot] Backend no disponible. Inicia con: uvicorn backend.main:app --reload');
    }
}

checkBackend();
