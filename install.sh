#!/bin/bash

APP_NAME="Exodus"
ICON_NAME="icon.png"
PY_FILE="exodus.py"
BUILD_DIR="dist"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"
BIN_DIR="$HOME/.local/bin"

echo "=== Building $APP_NAME ==="

# Проверка PyInstaller
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller не найден, ставим..."
    pip install --user pyinstaller
fi

# Сборка с PyInstaller с иконкой
pyinstaller --noconfirm --onefile --windowed --icon=$ICON_NAME $PY_FILE

# Создаём папку для бинарника, если нет
mkdir -p $BIN_DIR

# Копируем бинарник
cp $BUILD_DIR/$APP_NAME $BIN_DIR/$APP_NAME
chmod +x $BIN_DIR/$APP_NAME

# Копируем иконку в ~/.local/share/icons
ICON_DIR="$HOME/.local/share/icons"
mkdir -p $ICON_DIR
cp $ICON_NAME $ICON_DIR/$ICON_NAME

# Создаём .desktop файл
mkdir -p $(dirname $DESKTOP_FILE)
cat > $DESKTOP_FILE <<EOL
[Desktop Entry]
Name=$APP_NAME
Comment=Hacker Terminal
Exec=$BIN_DIR/$APP_NAME
Icon=$ICON_DIR/$ICON_NAME
Terminal=false
Type=Application
Categories=Utility;
EOL

chmod +x $DESKTOP_FILE

echo "=== Installation complete! ==="
echo "You can now launch $APP_NAME from your applications menu."
