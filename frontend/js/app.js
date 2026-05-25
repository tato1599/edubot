/**
 * EduBot Frontend v2.0 - Tema Rojo TecNM ITCJ
 * Animaciones GSAP épicas + Lógica del chat
 */

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
    initEpicAnimations();
    generateEnergyParticles();
    setupEventListeners();
    setupMagneticButtons();
    setupParallax();
});

// ── Animaciones ÉPICAS de entrada ──
function initEpicAnimations() {
    if (typeof gsap === 'undefined') {
        console.warn('[EduBot] GSAP no cargó. Usando UI sin animaciones.');
        return;
    }

    try {
        // Timeline maestra
        const masterTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
        
        // 1. Logo: aparece con escala + rotación + brillo
        masterTl.fromTo('.logo-container',
            { scale: 0, rotation: -180, opacity: 0 },
            { scale: 1, rotation: 0, opacity: 1, duration: 1.2, ease: 'back.out(1.7)' }
        )
        // 2. Anillos del logo: aparecen con delay escalonado
        .fromTo('.logo-ring',
            { scale: 0, opacity: 0 },
            { scale: 1, opacity: 1, stagger: 0.2, duration: 0.8, ease: 'back.out(1.5)' },
            '-=0.8'
        )
        // 3. Efecto de pulso continuo en el logo
        .add(() => {
            gsap.to('.logo-core', {
                boxShadow: '0 0 60px rgba(220, 38, 38, 0.6), 0 0 100px rgba(245, 158, 11, 0.3)',
                duration: 1.5,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
        }, '-=0.3')
        // 4. Título principal: efecto de typewriter + glow
        .fromTo('.title-line',
            { y: 60, opacity: 0, scale: 0.9 },
            { y: 0, opacity: 1, scale: 1, duration: 1, ease: 'power4.out' },
            '-=0.5'
        )
        // 5. Subtítulo: slide desde abajo con brillo dorado
        .fromTo('.title-sub',
            { y: 30, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.8, ease: 'power3.out' },
            '-=0.6'
        )
        // 6. Línea decorativa: dibujándose
        .fromTo('.title-sub::after',
            { scaleX: 0 },
            { scaleX: 1, duration: 0.6, ease: 'power2.out' },
            '-=0.3'
        )
        // 7. Descripción: fade in suave
        .fromTo('.welcome-desc',
            { y: 20, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.7 },
            '-=0.4'
        )
        // 8. Pills: aparecen con rebote elástico y rotación
        .fromTo('.pill',
            { scale: 0, opacity: 0, rotation: -15 },
            { scale: 1, opacity: 1, rotation: 0, stagger: 0.08, duration: 0.6, ease: 'elastic.out(1, 0.5)' },
            '-=0.3'
        )
        // 9. Botón: aparece con slide + glow
        .fromTo('.start-btn',
            { y: 50, opacity: 0, scale: 0.8 },
            { y: 0, opacity: 1, scale: 1, duration: 0.8, ease: 'back.out(1.7)' },
            '-=0.2'
        )
        // 10. Animación continua del botón (pulse)
        .add(() => {
            gsap.to('.start-btn', {
                boxShadow: '0 8px 32px rgba(220, 38, 38, 0.6), 0 0 60px rgba(220, 38, 38, 0.3), 0 0 100px rgba(245, 158, 11, 0.15)',
                duration: 2,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
        });

        // Animación flotante del logo (levitación)
        gsap.to('.logo-container', {
            y: -8,
            duration: 3,
            repeat: -1,
            yoyo: true,
            ease: 'sine.inOut'
        });

    } catch (e) {
        console.warn('[EduBot] Error en animaciones:', e);
    }
}

// ── Partículas de energía roja ──
function generateEnergyParticles() {
    for (let i = 0; i < 40; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.top = Math.random() * 100 + '%';
        const size = Math.random() * 5 + 2;
        p.style.width = size + 'px';
        p.style.height = size + 'px';
        p.style.opacity = Math.random() * 0.4 + 0.1;
        particlesContainer.appendChild(p);
        
        if (typeof gsap !== 'undefined') {
            try {
                // Movimiento hacia arriba con ondulación
                gsap.to(p, {
                    y: -150 - Math.random() * 250,
                    x: (Math.random() - 0.5) * 150,
                    opacity: 0,
                    duration: 4 + Math.random() * 6,
                    repeat: -1,
                    delay: Math.random() * 5,
                    ease: 'none'
                });
                
                // Pulso de brillo
                gsap.to(p, {
                    boxShadow: `0 0 ${Math.random() * 10 + 5}px rgba(220, 38, 38, 0.6)`,
                    duration: 1 + Math.random() * 2,
                    repeat: -1,
                    yoyo: true,
                    ease: 'sine.inOut'
                });
            } catch (e) {}
        }
    }
}

// ── Botones magnéticos (efecto hover) ──
function setupMagneticButtons() {
    if (typeof gsap === 'undefined') return;
    
    const buttons = document.querySelectorAll('.start-btn, .send-btn, .icon-btn');
    
    buttons.forEach(btn => {
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            gsap.to(btn, {
                x: x * 0.2,
                y: y * 0.2,
                duration: 0.3,
                ease: 'power2.out'
            });
        });
        
        btn.addEventListener('mouseleave', () => {
            gsap.to(btn, {
                x: 0,
                y: 0,
                duration: 0.5,
                ease: 'elastic.out(1, 0.3)'
            });
        });
    });
}

// ── Parallax sutil con mouse ──
function setupParallax() {
    if (typeof gsap === 'undefined') return;
    
    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 2;
        const y = (e.clientY / window.innerHeight - 0.5) * 2;
        
        gsap.to('.orb-1', { x: x * 30, y: y * 30, duration: 2, ease: 'power2.out' });
        gsap.to('.orb-2', { x: -x * 20, y: -y * 20, duration: 2, ease: 'power2.out' });
        gsap.to('.logo-container', { x: x * 10, y: y * 10, duration: 1, ease: 'power2.out' });
    });
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

// ── Navegación con transiciones épicas ──
function goToChat() {
    const switchToChat = () => {
        welcomeScreen.classList.add('hidden');
        chatScreen.classList.remove('hidden');
        chatScreen.style.opacity = '1';
        chatScreen.style.transform = 'none';
        
        // Animación de entrada del chat
        if (typeof gsap !== 'undefined') {
            try {
                gsap.fromTo('.chat-header', 
                    { y: -50, opacity: 0 },
                    { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }
                );
                gsap.fromTo('.chat-input-area',
                    { y: 50, opacity: 0 },
                    { y: 0, opacity: 1, duration: 0.6, delay: 0.2, ease: 'power3.out' }
                );
            } catch (e) {}
        }
        
        // Mostrar mensaje de bienvenida del bot
        setTimeout(() => {
            addBotMessage(
                "¡Hola! Soy EduBot, tu asistente del TecNM ITCJ.\n\n" +
                "Puedo ayudarte con:\n" +
                "• 🎓 Trámites escolares (inscripción, reinscripción, becas, titulación)\n" +
                "• 📚 Retícula de Ingeniería en Sistemas Computacionales\n" +
                "• 🍔 Locales de comida (Doña Pelos, Café Tec, Manos Sucias)\n" +
                "• 🥗 Nutrición SMAE y dietas económicas para estudiantes\n\n" +
                "¿En qué puedo ayudarte hoy?"
            );
        }, 400);
    };

    if (typeof gsap !== 'undefined') {
        try {
            // Animación de salida épica
            const tl = gsap.timeline({
                onComplete: switchToChat
            });
            
            tl.to('.welcome-content > *', {
                y: -30,
                opacity: 0,
                stagger: 0.05,
                duration: 0.4,
                ease: 'power2.in'
            })
            .to('.bg-mesh', {
                scale: 1.2,
                opacity: 0,
                duration: 0.5,
                ease: 'power2.in'
            }, '-=0.3');
            return;
        } catch (e) {
            console.warn('[EduBot] GSAP falló en transición:', e);
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
        
        // Re-iniciar animaciones de entrada
        if (typeof gsap !== 'undefined') {
            try {
                gsap.fromTo('.welcome-content > *',
                    { y: 30, opacity: 0 },
                    { y: 0, opacity: 1, stagger: 0.08, duration: 0.5, ease: 'power3.out' }
                );
            } catch (e) {}
        }
    };

    if (typeof gsap !== 'undefined') {
        try {
            gsap.to('.chat-screen', {
                opacity: 0,
                scale: 0.95,
                x: 50,
                duration: 0.4,
                ease: 'power2.in',
                onComplete: switchToWelcome
            });
            return;
        } catch (e) {}
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

function animateMessageIn(element) {
    element.style.opacity = '1';
    element.style.transform = 'translateY(0)';
    
    if (typeof gsap !== 'undefined') {
        try {
            gsap.fromTo(element,
                { opacity: 0, y: 30, scale: 0.95 },
                { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'power3.out' }
            );
            
            // Efecto de brillo en mensajes del bot
            if (element.classList.contains('bot')) {
                gsap.fromTo(element.querySelector('.message-content'),
                    { boxShadow: '0 0 0px rgba(220, 38, 38, 0)' },
                    { boxShadow: '0 0 30px rgba(220, 38, 38, 0.15)', duration: 0.8, ease: 'power2.out' }
                );
            }
        } catch (e) {}
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
    
    if (typeof gsap !== 'undefined') {
        try {
            gsap.fromTo(div, 
                { opacity: 0, y: 20 },
                { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }
            );
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
                    scale: 0.95,
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
