#!/bin/bash

# ============================================
# EXODUS Terminal - Installation Script
# ============================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для красивого вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# Конфигурация
# ============================================

APP_NAME="exodus"
APP_DISPLAY_NAME="EXODUS Terminal"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
PY_FILE="$REPO_DIR/exodus.py"
ICON_FILE="$REPO_DIR/exodus.png"

# Директории для установки
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_BASE_DIR="$HOME/.local/share/icons"
PIXMAPS_DIR="$HOME/.local/share/pixmaps"

# Путь к бинарнику
BUILD_DIR="$REPO_DIR/build"
DIST_DIR="$REPO_DIR/dist"
BINARY="$BIN_DIR/$APP_NAME"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"

# ============================================
# Проверки
# ============================================

print_info "Starting EXODUS Terminal installation..."
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed!"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Проверка файлов
if [ ! -f "$PY_FILE" ]; then
    print_error "exodus.py not found at: $PY_FILE"
    exit 1
fi
print_success "exodus.py found"

if [ ! -f "$ICON_FILE" ]; then
    print_warning "Icon file not found at: $ICON_FILE"
    print_warning "Will create a placeholder icon"
    # Создаём заглушку если иконки нет
    ICON_FILE=""
else
    print_success "Icon found"
fi

# ============================================
# Установка зависимостей
# ============================================

print_info "Checking dependencies..."

# Проверка и установка PyQt5
if ! python3 -c "import PyQt5" &> /dev/null; then
    print_warning "PyQt5 not found, installing..."
    pip3 install --user PyQt5
    print_success "PyQt5 installed"
else
    print_success "PyQt5 already installed"
fi

# Проверка и установка PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    print_warning "PyInstaller not found, installing..."
    pip3 install --user pyinstaller
    export PATH="$HOME/.local/bin:$PATH"
    print_success "PyInstaller installed"
else
    print_success "PyInstaller already installed"
fi

# ============================================
# Сборка приложения
# ============================================

print_info "Building $APP_DISPLAY_NAME..."

# Очистка старых сборок
rm -rf "$BUILD_DIR" "$DIST_DIR" "$REPO_DIR/$APP_NAME.spec"

# Сборка
if [ -n "$ICON_FILE" ]; then
    pyinstaller --noconfirm \
                --onefile \
                --windowed \
                --icon="$ICON_FILE" \
                --name "$APP_NAME" \
                --add-data "$ICON_FILE:." \
                "$PY_FILE"
else
    pyinstaller --noconfirm \
                --onefile \
                --windowed \
                --name "$APP_NAME" \
                "$PY_FILE"
fi

if [ ! -f "$DIST_DIR/$APP_NAME" ]; then
    print_error "Build failed! Binary not found."
    exit 1
fi

print_success "Build completed"

# ============================================
# Установка бинарника
# ============================================

print_info "Installing binary to $BIN_DIR..."

mkdir -p "$BIN_DIR"
cp "$DIST_DIR/$APP_NAME" "$BINARY"
chmod +x "$BINARY"

print_success "Binary installed: $BINARY"

# ============================================
# Установка иконки (множественные места)
# ============================================

if [ -n "$ICON_FILE" ]; then
    print_info "Installing icon..."
    
    # 1. Устанавливаем в pixmaps (старый стандарт, но работает везде)
    mkdir -p "$PIXMAPS_DIR"
    cp "$ICON_FILE" "$PIXMAPS_DIR/$APP_NAME.png"
    print_success "Icon installed to: $PIXMAPS_DIR/$APP_NAME.png"
    
    # 2. Устанавливаем в hicolor theme (современный стандарт)
    ICON_SIZES=("16x16" "22x22" "24x24" "32x32" "48x48" "64x64" "128x128" "256x256" "512x512")
    
    for size in "${ICON_SIZES[@]}"; do
        ICON_DIR="$ICON_BASE_DIR/hicolor/$size/apps"
        mkdir -p "$ICON_DIR"
        
        # Используем convert из ImageMagick если доступен, иначе просто копируем
        if command -v convert &> /dev/null; then
            convert "$ICON_FILE" -resize "$size" "$ICON_DIR/$APP_NAME.png" 2>/dev/null || \
            cp "$ICON_FILE" "$ICON_DIR/$APP_NAME.png"
        else
            cp "$ICON_FILE" "$ICON_DIR/$APP_NAME.png"
        fi
    done
    
    print_success "Icon installed to hicolor theme"
    
    # 3. Обновляем кэш иконок
    if command -v gtk-update-icon-cache &> /dev/null; then
        gtk-update-icon-cache -f -t "$ICON_BASE_DIR/hicolor" 2>/dev/null || true
        print_success "Icon cache updated"
    fi
    
    # Определяем какой путь к иконке использовать в .desktop
    ICON_PATH="$APP_NAME"  # Используем просто имя, система найдёт сама
else
    ICON_PATH=""
fi

# ============================================
# Создание .desktop файла
# ============================================

print_info "Creating desktop entry..."

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_DISPLAY_NAME
GenericName=Terminal Emulator
Comment=Advanced terminal emulator with PTY support
Exec=$BINARY
Icon=$ICON_PATH
Terminal=false
Categories=System;TerminalEmulator;Utility;ConsoleOnly;
Keywords=terminal;console;shell;command;cmd;bash;
StartupNotify=true
StartupWMClass=$APP_NAME
EOF

chmod +x "$DESKTOP_FILE"

print_success "Desktop file created: $DESKTOP_FILE"

# ============================================
# Обновление системных баз данных
# ============================================

print_info "Updating system databases..."

# Обновляем базу desktop файлов
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    print_success "Desktop database updated"
fi

# Обновляем MIME cache
if command -v update-mime-database &> /dev/null; then
    update-mime-database "$HOME/.local/share/mime" 2>/dev/null || true
fi

# Форсируем обновление меню (для разных DE)
if command -v xdg-desktop-menu &> /dev/null; then
    xdg-desktop-menu forceupdate 2>/dev/null || true
fi

# Обновляем кэш для GNOME
if [ "$XDG_CURRENT_DESKTOP" = "GNOME" ]; then
    if command -v killall &> /dev/null; then
        killall -SIGHUP gnome-shell 2>/dev/null || true
    fi
fi

# ============================================
# Проверка установки
# ============================================

print_info "Verifying installation..."

if [ -x "$BINARY" ]; then
    print_success "Binary is executable"
else
    print_error "Binary is not executable!"
fi

if [ -f "$DESKTOP_FILE" ]; then
    print_success "Desktop file exists"
else
    print_error "Desktop file not found!"
fi

# ============================================
# Завершение
# ============================================

echo ""
echo "=========================================="
print_success "Installation completed successfully!"
echo "=========================================="
echo ""
echo "Application Details:"
echo "  • Binary: $BINARY"
echo "  • Desktop file: $DESKTOP_FILE"
if [ -n "$ICON_FILE" ]; then
    echo "  • Icon: $PIXMAPS_DIR/$APP_NAME.png"
fi
echo ""
echo "You can now:"
echo "  1. Launch from applications menu: Search for 'EXODUS'"
echo "  2. Run from terminal: $APP_NAME"
echo "  3. Add to favorites/dock"
echo ""

if [ -n "$ICON_FILE" ]; then
    echo "If icon doesn't appear immediately:"
    echo "  • Log out and log back in"
    echo "  • Or restart your desktop environment"
    echo "  • For GNOME: Press Alt+F2, type 'r', press Enter"
    echo ""
fi

print_info "Cleaning up build files..."
rm -rf "$BUILD_DIR" "$REPO_DIR/$APP_NAME.spec"

echo ""
read -p "Do you want to launch EXODUS Terminal now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    nohup "$BINARY" > /dev/null 2>&1 &
    print_success "EXODUS Terminal launched!"
fi

echo ""
print_success "Installation script finished!"
