#!/bin/bash
# =====================================================================
# VOLT RECORDS UNIFIED NETWORK DISCOVERY & AI ANALYZER
# =====================================================================

REMOTE_USER="voltrecords1"
REMOTE_PASS="$(grep -m1 '^VOLT_SSH_PASS=' /Users/mtb/Omni-Studio/.env | cut -d= -f2-)"
REMOTE_HOST="10.0.0.250"
LOCAL_MOUNT="/Volumes/SuperMac"
OUTPUT_RAW="/Users/mtb/supermac_raw_blueprint.txt"

echo "🔌 [1/3] Mapping Network Share: Connecting Global SuperMac Drive..."

# Enforce local mount anchor point
if [ ! -d "$LOCAL_MOUNT" ]; then
    sudo mkdir -p "$LOCAL_MOUNT"
    sudo chown -R $(whoami) "$LOCAL_MOUNT"
fi

# Authenticate and mount root share if not already active
if mount | grep -q "$LOCAL_MOUNT"; then
    echo "  ✓ SuperMac is already mounted and active."
else
    mount_smbfs "//${REMOTE_USER}:${REMOTE_PASS}@${REMOTE_HOST}/${REMOTE_USER}" "$LOCAL_MOUNT" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ Success: Entire remote user home directory mounted to $LOCAL_MOUNT"
    else
        echo "  ✗ Error: Network connection timed out. Verify File Sharing is turned on on the second Mac."
        exit 1
    fi
fi

echo "📡 [2/3] Running Filtered Wireless Reconnaissance over SSH..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
    echo '=== ROOT HOME LEVEL ==='
    ls -la ~ 2>/dev/null

    echo '=== AUDIO & MIXING ENGINES ==='
    find ~/Omni-Studio ~/Music -maxdepth 4 -not -path '*/.*' 2>/dev/null

    echo '=== AGENT INFRASTRUCTURE ==='
    find ~/ruflo ~/plugins -maxdepth 3 -not -path '*/node_modules*' -not -path '*/.*' 2>/dev/null

    echo '=== UI DASHBOARDS & TSX PAGES ==='
    find ~/omni ~/cyphr-local -maxdepth 4 -not -path '*/node_modules*' -not -path '*/.*' -name '*.tsx' -o -name '*.ts' -o -name '*.js' 2>/dev/null

    echo '=== HISTORIC DEPLOYMENT SHARES ==='
    find ~/Public '/Users/voltrecords1/VOLT RECORDS’s Public Folder' '/Users/voltrecords1/Mykel T Brooks’s Public Folder' '/Users/voltrecords1/pmg' '/Users/voltrecords1/Waves' -maxdepth 3 -not -path '*/.*' 2>/dev/null
" > "$OUTPUT_RAW" 2>&1

if [ -s "$OUTPUT_RAW" ]; then
    echo "  ✓ Telemetry successfully cached locally at: $OUTPUT_RAW"
else
    echo "  ✗ Error: Captured network trace is empty or invalid."
    exit 1
fi

echo "🧠 [3/3] Invoking Qwen Core Swarm Intelligence Engine..."
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/Library/Application Support/Ollama:$PATH"

opencode run --dir "/Users/mtb" --model "ollama/qwen3:14b" \
  "Read the raw network telemetry file located at '$OUTPUT_RAW'.
   Thoroughly dissect the files, setups, and architectures mapped on the voltrecords1 machine.

   Provide a comprehensive, production-ready breakdown answering:
   1. **Exploitable Production Scripts:** What are scripts like master.py, generator.py, or start-autonomous.sh built to do? How do we pipe data into them?
   2. **Available Frontend Interfaces:** What UI elements (like Booking.tsx or Mixer.tsx) can we immediately launch to handle client-facing automation?
   3. **Vocal Processing & Prompt Assets:** What specific preset directories (Waves) or text blueprints (luna_vocal_chain_master_prompt.txt) can we hook into our A&R outreach pitches to land more studio sessions?
   4. **Immediate Strategic Roadmap:** Give Mykel a clean step-by-step checklist to bridge these assets together into an automated cash-flowing studio manager right now."