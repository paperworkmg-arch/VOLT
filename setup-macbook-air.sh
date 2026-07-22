#!/bin/bash
# ============================================
# Omni Studio - MacBook Air Setup Script
# Run this on Mykel's MacBook Air
# ============================================

echo "=========================================="
echo "  Omni Studio - MacBook Air Setup"
echo "=========================================="
echo ""

# Step 1: Update GitHub repo
echo "[1/4] Updating from GitHub..."
cd ~
if [ -d "pinokio/api/omni-studio" ]; then
    cd pinokio/api/omni-studio
    git pull origin main
    echo "✅ Repository updated"
else
    echo "Repository not found. Cloning..."
    mkdir -p pinokio/api
    cd pinokio/api
    git clone https://github.com/paperworkmg-arch/omni-studio.git
    cd omni-studio
    echo "✅ Repository cloned"
fi
echo ""

# Step 2: Find and delete old Omni-Studio
echo "[2/4] Looking for old Omni-Studio..."
OLD_PATHS=(
    "$HOME/Omni-Studio"
    "$HOME/Documents/Omni-Studio"
    "$HOME/Desktop/Omni-Studio"
    "$HOME/Projects/Omni-Studio"
)

FOUND=0
for path in "${OLD_PATHS[@]}"; do
    if [ -d "$path" ]; then
        echo "Found: $path"
        echo "Moving to Trash..."
        osascript -e "tell application \"Finder\" to delete (POSIX file \"$path\" as alias)" 2>/dev/null || mv "$path" ~/.Trash/
        echo "✅ Deleted: $path"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "No old Omni-Studio folder found"
fi
echo ""

# Step 3: Create desktop launchers
echo "[3/4] Creating desktop launchers..."
LAUNCHER_DIR="$HOME/Desktop"

# Main launcher
cat > "$LAUNCHER_DIR/Omni Studio.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../pinokio/api/omni-studio"
if command -v pinokio &> /dev/null; then
    pinokio start omni-studio
else
    cd app/dashboard
    [ ! -d "venv" ] && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt || source venv/bin/activate
    python omni.py &
    sleep 3
    open http://127.0.0.1:8500
fi
EOF
chmod +x "$LAUNCHER_DIR/Omni Studio.command"

# Freelance Bot launcher
cat > "$LAUNCHER_DIR/Freelance Bot.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../pinokio/api/omni-studio/app/omni-source"
python3 scripts/freelance_bot.py check
echo ""
read -p "Press Enter to exit..."
EOF
chmod +x "$LAUNCHER_DIR/Freelance Bot.command"

# Approval Monitor launcher
cat > "$LAUNCHER_DIR/Approval Monitor.command" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../pinokio/api/omni-studio/app/omni-source"
python3 scripts/approval_monitor.py
echo ""
read -p "Press Enter to exit..."
EOF
chmod +x "$LAUNCHER_DIR/Approval Monitor.command"

echo "✅ Desktop launchers created"
echo ""

# Step 4: Summary
echo "[4/4] Setup complete!"
echo ""
echo "=========================================="
echo "  What's on this computer now:"
echo "=========================================="
echo ""
echo "📱 GitHub Repo: ~/pinokio/api/omni-studio"
echo "🖥️  Desktop Launchers:"
echo "   - Omni Studio.command"
echo "   - Freelance Bot.command"
echo "   - Approval Monitor.command"
echo ""
echo "🗑️  Old Omni-Studio: Moved to Trash"
echo ""
echo "=========================================="
echo "  To empty Trash permanently:"
echo "=========================================="
echo "  Right-click Trash → Empty Trash"
echo ""
echo "Done! 🎉"
