/**
 * EduBot Frontend v2.0 - Tema Rojo TecNM ITCJ
 * Animaciones GSAP épicas + Lógica del chat
 */

const API_BASE = (window.location.protocol === 'file:') 
    ? 'http://localhost:8000' 
    : `${window.location.protocol}//${window.location.host}`;

// ── Detección de dispositivo ──
const IS_MOBILE = window.matchMedia('(hover: none) and (pointer: coarse)').matches 
    || ('ontouchstart' in window && navigator.maxTouchPoints > 0);

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
const systemStatus = document.getElementById('system-status');
const statusText = systemStatus?.querySelector('.status-text');
const statusProgressFill = systemStatus?.querySelector('.status-progress-fill');
const chatLoadingOverlay = document.getElementById('chat-loading-overlay');
const chatLoaderText = document.getElementById('chat-loader-text');
const chatLoaderSub = document.getElementById('chat-loader-sub');

let isWaiting = false;
let conversationHistory = [];
let backendReady = false;
let healthCheckInterval = null;

// ── Inicialización: mostrar UI inmediatamente, carga en segundo plano ──
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    startHealthPolling();
});

// Polling de /health en segundo plano (no bloquea la UI)
async function startHealthPolling() {
    const poll = async () => {
        try {
            const res = await fetch(`${API_BASE}/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            if (!res.ok) throw new Error('health not ok');
            const data = await res.json();
            updateSystemStatus(data);
            
            if (data.status === 'ready') {
                backendReady = true;
                if (healthCheckInterval) {
                    clearInterval(healthCheckInterval);
                    healthCheckInterval = null;
                }
            }
        } catch (e) {
            // Backend aún no responde (ni siquiera arrancó)
            updateSystemStatus({
                status: 'loading',
                stage: 'initializing',
                stage_name: 'Iniciando servidor...',
                progress: 0.0
            });
        }
    };
    
    // Primera llamada inmediata
    await poll();
    // Luego cada 2 segundos hasta que esté listo
    if (!backendReady) {
        healthCheckInterval = setInterval(poll, 2000);
    }
}

function updateSystemStatus(data) {
    if (!systemStatus || !statusText || !statusProgressFill) return;
    
    // Actualizar texto
    const stageName = data.stage_name || (data.status === 'ready' ? 'Sistema listo' : 'Cargando...');
    statusText.textContent = stageName;
    
    // Actualizar barra de progreso real
    const progress = Math.max(0, Math.min(1, data.progress || 0));
    statusProgressFill.style.width = `${Math.round(progress * 100)}%`;
    
    // Actualizar clases de estado
    systemStatus.classList.remove('ready', 'error');
    if (data.status === 'ready') {
        systemStatus.classList.add('ready');
    } else if (data.stage === 'error') {
        systemStatus.classList.add('error');
    }
}

function initApp() {
    if (!IS_MOBILE) {
        initSithCursor();
    }
    initEpicAnimations();
    if (!IS_MOBILE) {
        generateSaberSparks();
    }
    setupEventListeners();
    if (!IS_MOBILE) {
        setupMagneticButtons();
        setupParallax();
    }
    initGlitchEffect();
    initForceInput();
}

// ── 🗡️ CURSOR SITH CON TRAIL DE SABLE LÁSER ──
function initSithCursor() {
    // Crear cursor personalizado
    const cursor = document.createElement('div');
    cursor.className = 'sith-cursor';
    document.body.appendChild(cursor);
    
    // Array para el trail (rastro)
    const trails = [];
    const maxTrails = 15;
    
    for (let i = 0; i < maxTrails; i++) {
        const trail = document.createElement('div');
        trail.className = 'sith-trail';
        document.body.appendChild(trail);
        trails.push({ element: trail, x: 0, y: 0, life: 0 });
    }
    
    let mouseX = 0, mouseY = 0;
    let isHovering = false;
    
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        
        // Actualizar cursor principal
        cursor.style.left = mouseX + 'px';
        cursor.style.top = mouseY + 'px';
        
        // Actualizar trail
        for (let i = trails.length - 1; i > 0; i--) {
            trails[i].x = trails[i - 1].x;
            trails[i].y = trails[i - 1].y;
            trails[i].life = trails[i - 1].life;
        }
        trails[0].x = mouseX;
        trails[0].y = mouseY;
        trails[0].life = 1;
        
        // Renderizar trail
        trails.forEach((t, i) => {
            const opacity = (1 - i / maxTrails) * 0.6;
            const scale = 1 - i / maxTrails;
            t.element.style.left = t.x + 'px';
            t.element.style.top = t.y + 'px';
            t.element.style.opacity = opacity;
            t.element.style.transform = `translate(-50%, -50%) scale(${scale})`;
        });
    });
    
    // Detectar hover en elementos interactivos
    const interactiveElements = document.querySelectorAll('button, a, .pill, input, textarea');
    interactiveElements.forEach(el => {
        el.addEventListener('mouseenter', () => {
            isHovering = true;
            cursor.classList.add('hover');
        });
        el.addEventListener('mouseleave', () => {
            isHovering = false;
            cursor.classList.remove('hover');
        });
    });
    
    // Click con efecto de explosión de chispas
    document.addEventListener('click', (e) => {
        createSparkExplosion(e.clientX, e.clientY);
    });
}

function createSparkExplosion(x, y) {
    for (let i = 0; i < 8; i++) {
        const spark = document.createElement('div');
        spark.className = 'spark';
        spark.style.left = x + 'px';
        spark.style.top = y + 'px';
        document.body.appendChild(spark);
        
        const angle = (Math.PI * 2 * i) / 8;
        const distance = 30 + Math.random() * 30;
        
        gsap.to(spark, {
            x: Math.cos(angle) * distance,
            y: Math.sin(angle) * distance,
            opacity: 0,
            scale: 0,
            duration: 0.5 + Math.random() * 0.3,
            ease: 'power2.out',
            onComplete: () => spark.remove()
        });
    }
}

// ── ✨ CHISPAS DE SABLE LÁSER (partículas mejoradas) ──
function generateSaberSparks() {
    for (let i = 0; i < 50; i++) {
        const spark = document.createElement('div');
        spark.className = 'spark';
        spark.style.left = Math.random() * 100 + '%';
        spark.style.top = Math.random() * 100 + '%';
        const size = Math.random() * 4 + 1;
        spark.style.width = size + 'px';
        spark.style.height = size + 'px';
        spark.style.opacity = Math.random() * 0.5 + 0.2;
        particlesContainer.appendChild(spark);
        
        if (typeof gsap !== 'undefined') {
            // Movimiento errático como chispas de sable
            const tl = gsap.timeline({ repeat: -1, delay: Math.random() * 5 });
            
            tl.to(spark, {
                y: -100 - Math.random() * 200,
                x: (Math.random() - 0.5) * 200,
                opacity: 0,
                duration: 2 + Math.random() * 3,
                ease: 'power1.out'
            })
            .set(spark, {
                y: 0,
                x: 0,
                opacity: Math.random() * 0.5 + 0.2,
                left: Math.random() * 100 + '%',
                top: Math.random() * 100 + '%'
            });
            
            // Pulso de brillo intenso
            gsap.to(spark, {
                boxShadow: `0 0 ${Math.random() * 15 + 8}px rgba(220, 38, 38, 0.8), 0 0 ${Math.random() * 25 + 15}px rgba(239, 68, 68, 0.5)`,
                duration: 0.3 + Math.random() * 0.5,
                repeat: -1,
                yoyo: true,
                ease: 'sine.inOut'
            });
        }
    }
}

// ── ⚡ EFECTO GLITCH EN SUBTÍTULO ──
function initGlitchEffect() {
    const subtitle = document.querySelector('.title-sub');
    if (!subtitle) return;
    
    // Glitch aleatorio cada 5-10 segundos
    setInterval(() => {
        if (Math.random() > 0.7 && !chatScreen.classList.contains('hidden')) return; // No glitch en chat
        
        subtitle.classList.add('glitching');
        
        // Sonido visual (sin audio real, solo el efecto visual)
        setTimeout(() => {
            subtitle.classList.remove('glitching');
        }, 300);
    }, 6000 + Math.random() * 4000);
}

// ── 🌟 EFECTO FORCE EN INPUT ACTIVO ──
function initForceInput() {
    const wrapper = document.querySelector('.input-wrapper');
    if (!wrapper) return;
    
    messageInput.addEventListener('focus', () => {
        wrapper.classList.add('force-active');
    });
    
    messageInput.addEventListener('blur', () => {
        wrapper.classList.remove('force-active');
    });
}

// ── 🎭 EASTER EGGS SITH ──
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
    const lowerText = text.toLowerCase();
    for (const [key, response] of Object.entries(SITH_EASTER_EGGS)) {
        if (lowerText.includes(key)) {
            return response;
        }
    }
    return null;
}

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
    startBtn.addEventListener('click', (e) => {
        if (!backendReady) {
            // Mostrar overlay de carga dentro del chat mientras el modelo se inicializa
            showChatLoadingOverlay();
            // Escuchar cuando esté listo para hacer la transición automática
            const checkReady = setInterval(() => {
                if (backendReady) {
                    clearInterval(checkReady);
                    hideChatLoadingOverlay();
                    startBtn.classList.add('clicked');
                    setTimeout(() => goToChat(), 300);
                }
            }, 500);
            return;
        }
        
        // Efecto visual de activación
        startBtn.classList.add('clicked');
        
        // Pequeño delay para que se vea la animación del botón antes de la transición
        setTimeout(() => {
            goToChat();
        }, 300);
    });
    
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

// ── 💥 EXPLOSIÓN ÉPICA AL INICIAR CONVERSACIÓN ──
let activeSupernovaTl = null;

function goToChat() {
    if (typeof gsap === 'undefined') {
        switchToChatSimple();
        return;
    }
    
    // Limpiar cualquier estado residual de una vuelta anterior
    cleanupWelcomeState();
    
    // 1. CREAR EXPLOSIÓN DE PARTÍCULAS (optimizada, menos partículas)
    createSupernovaExplosion();
    
    // 2. TIMELINE ÉPICO (más corto y fluido)
    activeSupernovaTl = gsap.timeline({
        onComplete: () => {
            activeSupernovaTl = null;
            switchToChat();
        }
    });
    
    const tl = activeSupernovaTl;
    
    // Fase 1: Logo rota y escala (más rápido)
    tl.to('.logo-core', {
        scale: 1.5,
        rotation: 720,
        duration: 0.5,
        ease: 'power3.in'
    })
    // Fase 2: Anillos expanden explosivamente
    .to('.logo-ring', {
        scale: 3,
        opacity: 0,
        duration: 0.4,
        stagger: 0.08,
        ease: 'power3.out'
    }, '-=0.3')
    // Fase 3: Título escala con glow (usamos transform, no textShadow que causa repaint)
    .to('.title-line', {
        scale: 1.15,
        opacity: 0.3,
        duration: 0.25,
        ease: 'power3.in'
    }, '-=0.3')
    // Fase 4: Shake de cámara vía CSS (mucho más performante)
    .call(() => {
        welcomeScreen.classList.add('shaking');
        setTimeout(() => welcomeScreen.classList.remove('shaking'), 400);
    }, null, '-=0.15')
    // Fase 5: Zoom out masivo
    .to('.welcome-content', {
        scale: 2.5,
        opacity: 0,
        duration: 0.5,
        ease: 'power3.in'
    }, '-=0.1')
    // Fase 6: Fondo colapsa
    .to('.bg-mesh', {
        scale: 0.5,
        opacity: 0,
        duration: 0.4,
        ease: 'power2.in'
    }, '-=0.3')
    // Fase 7: Flash blanco rápido
    .call(() => {
        const flash = document.createElement('div');
        flash.className = 'flash-overlay';
        flash.style.cssText = 'position:fixed;inset:0;background:#fff;opacity:0.9;z-index:9999;pointer-events:none;';
        document.body.appendChild(flash);
        gsap.to(flash, {
            opacity: 0,
            duration: 0.35,
            ease: 'power2.in',
            onComplete: () => flash.remove()
        });
    }, null, '-=0.1');
    
    function switchToChat() {
        welcomeScreen.classList.add('hidden');
        chatScreen.classList.remove('hidden');
        
        // Animación de entrada del chat (más ligera)
        gsap.fromTo('.chat-screen', 
            { opacity: 0, scale: 0.9 },
            { opacity: 1, scale: 1, duration: 0.4, ease: 'power2.out' }
        );
        
        gsap.fromTo('.chat-header', 
            { y: -60, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.5, ease: 'power3.out', delay: 0.1 }
        );
        
        gsap.fromTo('.chat-messages',
            { opacity: 0 },
            { opacity: 1, duration: 0.4, delay: 0.2 }
        );
        
        gsap.fromTo('.chat-input-area',
            { y: 60, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.5, delay: 0.3, ease: 'power3.out' }
        );
        
        setTimeout(() => {
            addBotMessage(
                "¡SISTEMA ACTIVADO! Soy EduBot, tu asistente inteligente del TecNM ITCJ.\n\n" +
                "Estoy listo para ayudarte con:\n" +
                "• 🎓 Trámites escolares\n" +
                "• 📚 Retícula ISC\n" +
                "• 🍔 Locales de comida\n" +
                "• 🥗 Nutrición SMAE\n" +
                "• ⚖️ Reglamento TecNM\n\n" +
                "¿En qué puedo asistirte, Padawan?"
            );
        }, 600);
    }
}

// ── 🌟 SUPERNOVA EXPLOSION (optimizada) ──
function createSupernovaExplosion() {
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    const particleCount = IS_MOBILE ? 12 : 25; // Móvil: 12, Desktop: 25
    
    const fragment = document.createDocumentFragment();
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'supernova-particle';
        const size = Math.random() * 6 + 3;
        const color = Math.random() > 0.5 ? '#DC2626' : '#F59E0B';
        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            left: ${centerX}px;
            top: ${centerY}px;
            box-shadow: 0 0 10px ${color};
        `;
        fragment.appendChild(particle);
        
        const angle = (Math.PI * 2 * i) / particleCount + (Math.random() - 0.5) * 0.8;
        const distance = 200 + Math.random() * 350;
        
        gsap.to(particle, {
            x: Math.cos(angle) * distance,
            y: Math.sin(angle) * distance,
            scale: 0,
            opacity: 0,
            duration: 0.6 + Math.random() * 0.3,
            ease: 'power3.out',
            onComplete: () => particle.remove()
        });
    }
    
    document.body.appendChild(fragment);
    
    // Shockwave simplificado (1 anillo en vez de sombras complejas)
    const shockwave = document.createElement('div');
    shockwave.className = 'shockwave-ring';
    shockwave.style.cssText = `
        width: 80px;
        height: 80px;
        border: 3px solid rgba(220, 38, 38, 0.7);
        left: ${centerX - 40}px;
        top: ${centerY - 40}px;
    `;
    document.body.appendChild(shockwave);
    
    gsap.to(shockwave, {
        scale: 12,
        opacity: 0,
        duration: 0.8,
        ease: 'power3.out',
        onComplete: () => shockwave.remove()
    });
}

function switchToChatSimple() {
    welcomeScreen.classList.add('hidden');
    chatScreen.classList.remove('hidden');
    chatScreen.style.opacity = '1';
    
    setTimeout(() => {
        addBotMessage(
            "¡Hola! Soy EduBot, tu asistente del TecNM ITCJ.\n\n" +
            "¿En qué puedo ayudarte hoy?"
        );
    }, 300);
}

// ── ⏳ OVERLAY DE CARGA DENTRO DEL CHAT ──
function showChatLoadingOverlay() {
    if (!chatLoadingOverlay) return;
    welcomeScreen.classList.add('hidden');
    chatScreen.classList.remove('hidden');
    chatLoadingOverlay.classList.remove('hidden');
    
    // Actualizar texto según el estado real
    if (chatLoaderText && statusText) {
        chatLoaderText.textContent = statusText.textContent;
    }
}

function hideChatLoadingOverlay() {
    if (!chatLoadingOverlay) return;
    chatLoadingOverlay.classList.add('hidden');
}

// ── 🧹 LIMPIAR TODO ESTADO DE ANIMACIONES ──
function cleanupWelcomeState() {
    // 1. Matar timeline activo
    if (activeSupernovaTl) {
        activeSupernovaTl.kill();
        activeSupernovaTl = null;
    }
    
    // 2. Limpiar partículas y shockwave huérfanos
    document.querySelectorAll('.supernova-particle, .shockwave-ring, .flash-overlay').forEach(el => el.remove());
    
    // 3. Resetear clases del welcome screen
    welcomeScreen.classList.remove('shaking');
    
    // 4. Resetear estilos inline del logo
    const logoCore = document.querySelector('.logo-core');
    const logoRings = document.querySelectorAll('.logo-ring');
    const titleLine = document.querySelector('.title-line');
    const bgMesh = document.querySelector('.bg-mesh');
    
    if (logoCore) gsap.set(logoCore, { clearProps: 'all' });
    if (titleLine) gsap.set(titleLine, { clearProps: 'all' });
    if (bgMesh) gsap.set(bgMesh, { clearProps: 'all' });
    logoRings.forEach(ring => gsap.set(ring, { clearProps: 'all' }));
    
    // 5. Resetear botón start
    startBtn.classList.remove('clicked');
    
    // 6. Asegurar que welcome-content sea visible
    const welcomeContent = document.querySelector('.welcome-content');
    if (welcomeContent) {
        welcomeContent.style.opacity = '1';
        welcomeContent.style.transform = 'none';
    }
}

function goToWelcome() {
    const switchToWelcome = () => {
        // Limpiar TODO antes de mostrar
        cleanupWelcomeState();
        
        chatScreen.classList.add('hidden');
        welcomeScreen.classList.remove('hidden');
        welcomeScreen.style.opacity = '1';
        welcomeScreen.style.transform = 'none';
        chatMessages.innerHTML = '';
        
        // Limpiar historial de conversación al salir del chat
        conversationHistory = [];
        updateMemoryIndicator();
        
        // Re-iniciar animaciones de entrada
        if (typeof gsap !== 'undefined') {
            try {
                gsap.fromTo('.welcome-content > *',
                    { y: 20, opacity: 0 },
                    { y: 0, opacity: 1, stagger: 0.06, duration: 0.4, ease: 'power3.out' }
                );
            } catch (e) {}
        }
    };

    if (typeof gsap !== 'undefined') {
        try {
            gsap.to('.chat-screen', {
                opacity: 0,
                scale: 0.95,
                duration: 0.3,
                ease: 'power2.in',
                onComplete: switchToWelcome
            });
            return;
        } catch (e) {}
    }
    switchToWelcome();
}

// ── Actualizar indicador de memoria ──
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

// ── Chat Functions ──
function handleSend() {
    const text = messageInput.value.trim();
    if (!text || isWaiting) return;
    
    // Agregar mensaje del usuario al historial
    conversationHistory.push({ role: "user", content: text });
    updateMemoryIndicator();
    
    addUserMessage(text);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Verificar easter eggs Sith primero (no usan API)
    const easterEgg = checkSithEasterEgg(text);
    if (easterEgg) {
        showTyping();
        setTimeout(() => {
            addBotMessage(easterEgg);
            // Agregar respuesta del bot al historial
            conversationHistory.push({ role: "assistant", content: easterEgg });
            // Limitar historial a 10 mensajes (5 turnos)
            if (conversationHistory.length > 10) {
                conversationHistory = conversationHistory.slice(-10);
            }
            updateMemoryIndicator();
        }, 800 + Math.random() * 600);
        return;
    }
    
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

// ── API Communication (STREAMING con MEMORIA) ──
async function sendToAPI(message) {
    try {
        // Usar el endpoint de streaming, enviando historial de conversación
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: conversationHistory })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        // Leer el stream
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
            
            // Procesar eventos SSE (separados por \n\n)
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Mantener la última línea incompleta
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.type === 'sources') {
                        currentSources = data.sources || [];
                    }
                    else if (data.type === 'token') {
                        // Primera vez: crear el elemento del mensaje
                        if (!messageElement) {
                            hideTyping();
                            messageElement = createMessageElement('bot', '');
                            chatMessages.appendChild(messageElement);
                            contentElement = messageElement.querySelector('.message-content p');
                            scrollToBottom();
                            
                            // Animar entrada
                            gsap.fromTo(messageElement,
                                { opacity: 0, y: 30, scale: 0.95 },
                                { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'power3.out' }
                            );
                        }
                        
                        // Agregar texto
                        currentMessage += data.text;
                        if (contentElement) {
                            contentElement.innerHTML = currentMessage
                                .replace(/\n\n/g, '</p><p>')
                                .replace(/\n/g, '<br>');
                        }
                        scrollToBottom();
                    }
                    else if (data.type === 'done') {
                        // Agregar fuentes al final
                        if (messageElement && currentSources.length > 0) {
                            const pillsDiv = document.createElement('div');
                            pillsDiv.style.marginTop = '0.5rem';
                            pillsDiv.style.display = 'flex';
                            pillsDiv.style.flexWrap = 'wrap';
                            pillsDiv.style.gap = '0.4rem';
                            
                            currentSources.forEach(src => {
                                const pill = document.createElement('span');
                                pill.className = 'source-pill';
                                pill.innerHTML = `📄 ${src.titulo} <span style="opacity:0.6">• ${src.categoria}</span>`;
                                pillsDiv.appendChild(pill);
                            });
                            
                            const content = messageElement.querySelector('.message-content');
                            if (content) content.appendChild(pillsDiv);
                        }
                        
                        // Guardar respuesta completa del bot en el historial
                        if (currentMessage) {
                            conversationHistory.push({ role: "assistant", content: currentMessage });
                            // Limitar historial a 10 mensajes (5 turnos) para no exceder tokens
                            if (conversationHistory.length > 10) {
                                conversationHistory = conversationHistory.slice(-10);
                            }
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
            "Por favor verifica que:\n" +
            "1. El backend está corriendo: `python backend/main.py`\n" +
            "2. La URL de la API es correcta: " + API_BASE + "\n\n" +
            "Error: " + error.message
        );
        isWaiting = false;
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
