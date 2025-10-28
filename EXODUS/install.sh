#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"

APP_NAME="exodus"
ICON_NAME="icon.png"
PY_FILE="exodus.py"
REPO_DIR="$(pwd)/EXODUS"  # Путь к папке с .py и иконкой
BUILD_DIR="dist"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"

echo "=== Installing $APP_NAME ==="

# Проверка PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller не найден, ставим..."
    pip install --user pyinstaller
fi

# Сборка с PyInstaller с иконкой и правильным именем
pyinstaller --noconfirm --onefile --windowed --icon="$REPO_DIR/$ICON_NAME" --name "$APP_NAME" "$REPO_DIR/$PY_FILE"

# Проверяем, что бинарник реально создан
if [ ! -f "$BUILD_DIR/$APP_NAME" ]; then
    echo "Ошибка: бинарник $BUILD_DIR/$APP_NAME не найден!"
    exit 1
fi

# Создаём папку для бинарника и копируем
mkdir -p "$BIN_DIR"
cp "$BUILD_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
chmod +x "$BIN_DIR/$APP_NAME"

# Копируем иконку
mkdir -p "$ICON_DIR"
cp "$REPO_DIR/$ICON_NAME" "$ICON_DIR/$ICON_NAME"

# Создаём .desktop файл
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOL
[Desktop Entry]
Name=$APP_NAME
Comment=Hacker Terminal
Exec=$BIN_DIR/$APP_NAME
Icon=$ICON_DIR/$ICON_NAME
Terminal=false
Type=Application
Categories=Utility;
EOL

chmod +x "$DESKTOP_FILE"

# Обновляем базу меню (чтобы .desktop появился сразу)
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" &> /dev/null
fi

echo "=== Installation complete! ==="
echo "You can now launch $APP_NAME from your applications menu or by typing '$APP_NAME' in terminal."
