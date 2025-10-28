#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"

REPO_DIR="$HOME/EXODUS-Terminal/EXODUS"  # путь к папке с exodus.py
APP_NAME="exodus"
PY_FILE="$REPO_DIR/exodus.py"
ICON_NAME="$REPO_DIR/exodus.png"
BUILD_DIR="$REPO_DIR/dist"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

echo "=== Building $APP_NAME ==="

# Проверка PyInstaller
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller не найден, ставим..."
    pip install --user pyinstaller
fi

# Сборка с PyInstaller с иконкой
pyinstaller --noconfirm --onefile --windowed --icon="$ICON_NAME" --name "$APP_NAME" "$PY_FILE"

# Создаём папку для бинарника, если нет
mkdir -p "$BIN_DIR"

# Копируем бинарник
cp "$BUILD_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"

# Копируем иконку в правильную директорию
mkdir -p "$ICON_DIR"
cp "$ICON_NAME" "$ICON_DIR/$APP_NAME.png"

# Обновляем кэш иконок
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# Создаём .desktop файл с АБСОЛЮТНЫМ путём (без ~)
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Version=1.0
Name=EXODUS Terminal
Comment=Advanced Hacker Terminal Emulator
Exec=$BIN_DIR/$APP_NAME
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=System;TerminalEmulator;Utility;
StartupNotify=true
Keywords=terminal;console;shell;
EOL

chmod +x "$DESKTOP_FILE"

# Обновляем базу данных desktop файлов
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "=== Installation complete! ==="
echo "Installed to: $BIN_DIR/$APP_NAME"
echo "Desktop file: $DESKTOP_FILE"
echo "Icon: $ICON_DIR/$APP_NAME.png"
echo ""
echo "If icon doesn't appear immediately, try:"
echo "1. Log out and log back in"
echo "2. Or run: gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor"
echo ""
echo "You can now launch $APP_NAME from your applications menu."
