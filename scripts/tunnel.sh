#!/bin/bash
# ──────────────────────────────────────────────────────────────
# EduBot Tunnel Manager v2.0
# Script profesional para gestionar tunnels de Cloudflare
# Uso: ./scripts/tunnel.sh [comando] [opciones]
# ──────────────────────────────────────────────────────────────

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

PORT=8000
PROVIDER="cloudflare"

# ───────────────────────────────────────────────
# Funciones de utilidad
# ───────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}           ${BOLD}EduBot Tunnel Manager v2.0${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# ───────────────────────────────────────────────
# Comandos
# ───────────────────────────────────────────────

cmd_help() {
    print_banner
    echo -e "${BOLD}Uso:${NC} ./scripts/tunnel.sh [comando] [opciones]"
    echo ""
    echo -e "${BOLD}Comandos disponibles:${NC}"
    echo ""
    echo "  ${CYAN}create${NC} [provider]    Crear un nuevo tunnel"
    echo "                       provider: cloudflare (default) | localtunnel"
    echo ""
    echo "  ${CYAN}list${NC}               Listar tunnels activos"
    echo ""
    echo "  ${CYAN}close${NC} [id|all]    Cerrar tunnel(s)"
    echo "                       'all' para cerrar todos"
    echo ""
    echo "  ${CYAN}status${NC}             Verificar dependencias"
    echo ""
    echo "  ${CYAN}interactive${NC}        Modo interactivo (menu)"
    echo ""
    echo "  ${CYAN}help${NC}               Mostrar esta ayuda"
    echo ""
    echo -e "${BOLD}Ejemplos:${NC}"
    echo "  ./scripts/tunnel.sh create"
    echo "  ./scripts/tunnel.sh create localtunnel"
    echo "  ./scripts/tunnel.sh list"
    echo "  ./scripts/tunnel.sh close all"
    echo ""
}

cmd_status() {
    print_banner
    echo -e "${BOLD}Estado de dependencias:${NC}"
    echo ""
    
    # Verificar cloudflared
    if command -v cloudflared &> /dev/null; then
        VERSION=$(cloudflared --version 2>/dev/null | head -1 || echo "unknown")
        print_success "cloudflared instalado ($VERSION)"
    else
        print_error "cloudflared NO instalado"
        echo "   Instala: curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb"
    fi
    echo ""
    
    # Verificar npx
    if command -v npx &> /dev/null; then
        VERSION=$(npx --version 2>/dev/null || echo "unknown")
        print_success "npx instalado ($VERSION)"
    else
        print_error "npx NO instalado"
        echo "   Instala Node.js: https://nodejs.org/"
    fi
    echo ""
    
    # Verificar backend
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        print_success "Backend respondiendo en puerto $PORT"
    else
        print_warn "Backend NO respondiendo en puerto $PORT"
        echo "   Inicia primero: ./start.sh"
    fi
    echo ""
}

cmd_create() {
    local provider="${1:-cloudflare}"
    
    print_banner
    
    # Verificar dependencias
    if [ "$provider" = "cloudflare" ]; then
        if ! command -v cloudflared &> /dev/null; then
            print_error "cloudflared no esta instalado."
            echo ""
            echo "Para instalar en Linux:"
            echo "  curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
            echo "  sudo dpkg -i cloudflared.deb"
            echo ""
            echo "Otras plataformas: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
            exit 1
        fi
    elif [ "$provider" = "localtunnel" ]; then
        if ! command -v npx &> /dev/null; then
            print_error "npx no esta instalado."
            echo "  Instala Node.js desde: https://nodejs.org/"
            exit 1
        fi
    else
        print_error "Provider no soportado: $provider"
        echo "  Providers validos: cloudflare, localtunnel"
        exit 1
    fi
    
    # Verificar backend
    if ! curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        print_warn "Backend no respondiendo en puerto $PORT"
        read -p "¿Quieres iniciar el backend primero? (s/N): " start_backend
        if [[ "$start_backend" =~ ^[Ss]$ ]]; then
            print_info "Iniciando backend..."
            # Verificar si estamos en entorno virtual
            if [ -z "$VIRTUAL_ENV" ] && [ -d "venv" ]; then
                source venv/bin/activate
            fi
            python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT &
            BACKEND_PID=$!
            
            # Esperar
            print_info "Esperando backend..."
            for i in {1..30}; do
                if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
                    print_success "Backend listo!"
                    break
                fi
                sleep 1
            done
            
            trap 'kill $BACKEND_PID 2>/dev/null; exit' INT TERM
        else
            print_error "Backend requerido para crear tunnel"
            exit 1
        fi
    fi
    
    echo ""
    print_info "Creando tunnel con ${BOLD}$provider${NC}..."
    echo "   Puerto local: $PORT"
    echo "   Esto puede tomar 5-15 segundos..."
    echo ""
    
    if [ "$provider" = "cloudflare" ]; then
        # Usar cloudflared directamente con captura de output
        TEMP_LOG=$(mktemp)
        
        cloudflared tunnel --url http://localhost:$PORT > "$TEMP_LOG" 2>&1 &
        TUNNEL_PID=$!
        
        # Esperar URL
        URL=""
        for i in {1..60}; do
            if [ -s "$TEMP_LOG" ]; then
                URL=$(grep -oP 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$TEMP_LOG" | head -1)
                if [ -n "$URL" ]; then
                    break
                fi
            fi
            sleep 1
        done
        
        if [ -n "$URL" ]; then
            echo ""
            echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║${NC}              ${BOLD}🌐 TUNNEL CREADO EXITOSAMENTE${NC}                ${GREEN}║${NC}"
            echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "   ${BOLD}URL Publica:${NC} ${CYAN}${URL}${NC}"
            echo -e "   ${BOLD}Provider:${NC}    Cloudflare Tunnel"
            echo -e "   ${BOLD}Local:${NC}       http://localhost:$PORT"
            echo ""
            echo -e "   ${YELLOW}📋 Comparte esta URL con tus companeros:${NC}"
            echo -e "   ${CYAN}${URL}${NC}"
            echo ""
            echo -e "   ${YELLOW}⚠️  Notas importantes:${NC}"
            echo "   • Manten esta terminal abierta"
            echo "   • Presiona Ctrl+C para cerrar el tunnel"
            echo "   • La URL es temporal (cambia al reiniciar)"
            echo ""
            echo -e "   ${GREEN}Para cerrar:${NC} Presiona Ctrl+C o corre './scripts/tunnel.sh close all'"
            echo ""
            
            # Guardar PID para poder cerrar despues
            echo "$TUNNEL_PID $URL" > .tunnel_info
            
            wait $TUNNEL_PID
        else
            print_error "No se pudo obtener URL del tunnel"
            echo "Output:"
            cat "$TEMP_LOG"
            kill $TUNNEL_PID 2>/dev/null || true
        fi
        
        rm -f "$TEMP_LOG"
        
    elif [ "$provider" = "localtunnel" ]; then
        TEMP_LOG=$(mktemp)
        
        npx localtunnel --port $PORT > "$TEMP_LOG" 2>&1 &
        TUNNEL_PID=$!
        
        URL=""
        for i in {1..60}; do
            if [ -s "$TEMP_LOG" ]; then
                URL=$(grep -oP 'https://[a-zA-Z0-9-]+\.loca\.lt' "$TEMP_LOG" | head -1)
                if [ -n "$URL" ]; then
                    break
                fi
            fi
            sleep 1
        done
        
        if [ -n "$URL" ]; then
            echo ""
            echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║${NC}              ${BOLD}🌐 TUNNEL CREADO EXITOSAMENTE${NC}                ${GREEN}║${NC}"
            echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "   ${BOLD}URL Publica:${NC} ${CYAN}${URL}${NC}"
            echo -e "   ${BOLD}Provider:${NC}    LocalTunnel"
            echo -e "   ${BOLD}Local:${NC}       http://localhost:$PORT"
            echo ""
            echo -e "   ${YELLOW}📋 Comparte esta URL con tus companeros:${NC}"
            echo -e "   ${CYAN}${URL}${NC}"
            echo ""
            echo "   ⚠️  Nota: LocalTunnel a veces pide verificacion."
            echo "      Si aparece un boton 'Click to Continue', tu companero debe hacer click."
            echo ""
            
            echo "$TUNNEL_PID $URL" > .tunnel_info
            wait $TUNNEL_PID
        else
            print_error "No se pudo obtener URL del tunnel"
            echo "Output:"
            cat "$TEMP_LOG"
            kill $TUNNEL_PID 2>/dev/null || true
        fi
        
        rm -f "$TEMP_LOG"
    fi
}

cmd_list() {
    print_banner
    echo -e "${BOLD}Tunnels activos:${NC}"
    echo ""
    
    if [ -f .tunnel_info ]; then
        while IFS= read -r line; do
            PID=$(echo "$line" | awk '{print $1}')
            URL=$(echo "$line" | awk '{print $2}')
            if kill -0 "$PID" 2>/dev/null; then
                echo -e "  ${GREEN}●${NC} PID: $PID | URL: ${CYAN}${URL}${NC}"
            else
                echo -e "  ${RED}●${NC} PID: $PID | URL: ${URL} ${RED}(muerto)${NC}"
            fi
        done < .tunnel_info
    else
        print_info "No hay tunnels registrados"
    fi
    echo ""
}

cmd_close() {
    local target="${1:-all}"
    
    print_banner
    
    if [ "$target" = "all" ]; then
        print_info "Cerrando todos los tunnels..."
        
        if [ -f .tunnel_info ]; then
            while IFS= read -r line; do
                PID=$(echo "$line" | awk '{print $1}')
                if kill -0 "$PID" 2>/dev/null; then
                    print_info "Cerrando PID $PID..."
                    kill "$PID" 2>/dev/null || true
                    sleep 1
                    if kill -0 "$PID" 2>/dev/null; then
                        kill -9 "$PID" 2>/dev/null || true
                    fi
                fi
            done < .tunnel_info
            rm -f .tunnel_info
            print_success "Todos los tunnels cerrados"
        else
            # Intentar matar cloudflared y npx localtunnel
            pkill -f "cloudflared tunnel" 2>/dev/null || true
            pkill -f "localtunnel" 2>/dev/null || true
            print_success "Procesos de tunneling cerrados"
        fi
    else
        # Cerrar tunnel especifico
        if kill -0 "$target" 2>/dev/null; then
            print_info "Cerrando PID $target..."
            kill "$target" 2>/dev/null || true
            sleep 1
            print_success "Tunnel cerrado"
        else
            print_error "PID $target no encontrado o no es un tunnel"
        fi
    fi
    echo ""
}

cmd_interactive() {
    while true; do
        clear
        print_banner
        
        echo -e "${BOLD}Menu Principal:${NC}"
        echo ""
        echo "  1) Crear tunnel con Cloudflare (recomendado)"
        echo "  2) Crear tunnel con LocalTunnel"
        echo "  3) Listar tunnels activos"
        echo "  4) Cerrar todos los tunnels"
        echo "  5) Verificar estado"
        echo "  6) Salir"
        echo ""
        read -p "Selecciona una opcion (1-6): " option
        
        case $option in
            1) cmd_create "cloudflare" ;;
            2) cmd_create "localtunnel" ;;
            3) cmd_list ; read -p "Presiona ENTER para continuar..." ;;
            4) cmd_close "all" ; read -p "Presiona ENTER para continuar..." ;;
            5) cmd_status ; read -p "Presiona ENTER para continuar..." ;;
            6) echo "Saliendo..."; exit 0 ;;
            *) print_error "Opcion invalida" ; sleep 1 ;;
        esac
    done
}

# ───────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────

main() {
    local cmd="${1:-interactive}"
    shift || true
    
    case "$cmd" in
        create) cmd_create "$@" ;;
        list) cmd_list ;;
        close) cmd_close "$@" ;;
        status) cmd_status ;;
        interactive) cmd_interactive ;;
        help|--help|-h) cmd_help ;;
        *) 
            print_error "Comando desconocido: $cmd"
            cmd_help
            exit 1
            ;;
    esac
}

main "$@"
