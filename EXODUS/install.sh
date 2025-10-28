#!/bin/bash

# ============================================
# EXODUS Terminal - Safe Installation Script
# ============================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================
# Конфигурация
# ============================================

APP_NAME="exodus"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_FILE="$SCRIPT_DIR/exodus.py"
ICON_FILE="$SCRIPT_DIR/exodus.svg"

BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/pixmaps"

BINARY="$BIN_DIR/$APP_NAME"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   EXODUS Terminal - Installation      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# ============================================
# Проверки
# ============================================

print_info "Checking requirements..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found!"
    exit 1
fi

if [ ! -f "$PY_FILE" ]; then
    print_error "exodus.py not found at: $PY_FILE"
    exit 1
fi

if [ ! -f "$ICON_FILE" ]; then
    print_warning "Icon not found, continuing without icon"
    ICON_FILE=""
fi

print_success "All checks passed"

# ============================================
# Установка зависимостей
# ============================================

print_info "Checking Python dependencies..."

if ! python3 -c "import PyQt5" &> /dev/null; then
    print_info "Installing PyQt5..."
    pip3 install --user PyQt5 || {
        print_error "Failed to install PyQt5"
        exit 1
    }
fi

if ! command -v pyinstaller &> /dev/null; then
    print_info "Installing PyInstaller..."
    pip3 install --user pyinstaller
    export PATH="$HOME/.local/bin:$PATH"
fi

print_success "Dependencies ready"

# ============================================
# Сборка
# ============================================

print_info "Building application (this may take a minute)..."

# Очистка старых файлов
rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist" "$SCRIPT_DIR/$APP_NAME.spec" 2>/dev/null

# Сборка с иконкой или без
if [ -n "$ICON_FILE" ]; then
    pyinstaller --noconfirm --onefile --windowed \
                --icon="$ICON_FILE" \
                --name "$APP_NAME" \
                "$PY_FILE" > /dev/null 2>&1
else
    pyinstaller --noconfirm --onefile --windowed \
                --name "$APP_NAME" \
                "$PY_FILE" > /dev/null 2>&1
fi

if [ ! -f "$SCRIPT_DIR/dist/$APP_NAME" ]; then
    print_error "Build failed!"
    exit 1
fi

print_success "Build completed"

# ============================================
# Установка
# ============================================

print_info "Installing binary..."

mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/dist/$APP_NAME" "$BINARY"
chmod +x "$BINARY"

print_success "Binary installed to: $BINARY"

# ============================================
# Иконка (простая установка)
# ============================================

if [ -n "$ICON_FILE" ]; then
    print_info "Installing icon..."
    
    mkdir -p "$ICON_DIR"
    cp "$ICON_FILE" "$ICON_DIR/$APP_NAME.svg"
    
    # ТОЛЬКО в pixmaps, без обновления кэшей
    ICON_PATH="$ICON_DIR/$APP_NAME.svg"
    
    print_success "Icon installed to: $ICON_PATH"
else
    ICON_PATH=""
fi

# ============================================
# Desktop файл
# ============================================

print_info "Creating desktop entry..."

mkdir -p "$DESKTOP_DIR"

# Используем ПОЛНЫЙ путь к иконке, чтобы избежать проблем с кэшем
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=EXODUS Terminal
GenericName=Terminal
Comment=Advanced terminal emulator
Exec=$BINARY
Icon=$ICON_PATH
Terminal=false
Categories=System;TerminalEmulator;
Keywords=terminal;console;shell;
StartupNotify=false
EOF

chmod +x "$DESKTOP_FILE"

print_success "Desktop file created"

# ============================================
# БЕЗОПАСНОЕ обновление (без зависаний)
# ============================================

print_info "Updating application database..."

# Только update-desktop-database, БЕЗ иконок и gnome-shell
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# ============================================
# Очистка
# ============================================

print_info "Cleaning up..."
rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/$APP_NAME.spec"

# ============================================
# Завершение
# ============================================

echo ""
echo "╔════════════════════════════════════════╗"
echo "║      Installation Complete! ✓          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Installation details:"
echo "  Binary:  $BINARY"
echo "  Desktop: $DESKTOP_FILE"
if [ -n "$ICON_PATH" ]; then
    echo "  Icon:    $ICON_PATH"
fi
echo ""
echo "Launch options:"
echo "  1. Type 'exodus' in terminal"
echo "  2. Search for 'EXODUS' in applications"
echo ""

if [ -n "$ICON_PATH" ]; then
    print_warning "Note: Icon may require logout/login to appear"
    echo ""
fi

read -p "Launch EXODUS now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting EXODUS Terminal..."
    "$BINARY" &
    sleep 1
    print_success "Launched!"
fi

echo ""
print_success "Done! Enjoy EXODUS Terminal 🚀"
echo ""
