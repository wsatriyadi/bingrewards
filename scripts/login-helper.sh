#!/usr/bin/env bash
# Login helper: buka Chrome GUI di server via browser (noVNC) untuk login akun MS.
# Pakai: ./login-helper.sh <nama-profil>     (mis. ./login-helper.sh akun1)
# Lalu buka http://192.168.110.8:6080/vnc.html di PC, login live.com, lalu Enter di sini.

set -euo pipefail

PROFILE="${1:-akun1}"
DISPLAY_NUM=":99"
VNC_PORT="6080"
DATA_DIR="$HOME/bingrewards/chrome-$PROFILE"

mkdir -p "$DATA_DIR"

echo "== Menghapus session lama (jika ada) =="
pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null || true
pkill -f "x11vnc.*rfbport 5900" 2>/dev/null || true
pkill -f "websockify.*$VNC_PORT" 2>/dev/null || true
sleep 1

echo "== Start Xvfb =="
Xvfb $DISPLAY_NUM -screen 0 1280x900x24 &
XVFB_PID=$!
sleep 2

echo "== Start Chrome headful =="
DISPLAY=$DISPLAY_NUM google-chrome \
    --user-data-dir="$DATA_DIR" \
    --no-first-run --no-default-browser-check \
    --window-size=1280,900 \
    "https://login.live.com/" &
CHROME_PID=$!
sleep 5

echo "== Start x11vnc + noVNC =="
x11vnc -display $DISPLAY_NUM -rfbport 5900 -nopw -shared -forever -quiet &
VNC_PID=$!
websockify --web /usr/share/novnc $VNC_PORT localhost:5900 &
WS_PID=$!
sleep 2

echo ""
echo "==================================================="
echo " BUKA di browser PC: http://192.168.110.8:6080/vnc.html"
echo " Login akun Microsoft di Chrome yang terbuka."
echo " Setelah selesai, tekan ENTER di sini untuk menutup."
echo "==================================================="
read -r _

echo "== Bersihkan =="
kill $WS_PID $VNC_PID $CHROME_PID $XVFB_PID 2>/dev/null || true
sleep 2
pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null || true
pkill -f "x11vnc.*rfbport 5900" 2>/dev/null || true
pkill -f "websockify.*$VNC_PORT" 2>/dev/null || true

echo "Selesai. Tambahkan akun di web UI:"
echo "  name: $PROFILE"
echo "  user_data_dir: $DATA_DIR"
