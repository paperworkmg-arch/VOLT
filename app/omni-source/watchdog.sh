#!/bin/bash

LEADS_DIR="$HOME/Omni-Studio/Incoming_Leads"
CLOSED_DIR="$HOME/Omni-Studio/Closed_Deals"
PITCH_QUEUE="$HOME/Omni-Studio/Outbound_Pitches"
PID_FILE="/tmp/volt_watchdog.pid"
LOG_FILE="$HOME/Omni-Studio/logs/watchdog.log"
SLEEP_INTERVAL=5

mkdir -p "$LEADS_DIR" "$CLOSED_DIR" "$PITCH_QUEUE"

cleanup() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Volt Watchdog shutting down." >> "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup INT TERM

if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "Watchdog already running (PID $old_pid). Exiting."
        exit 1
    fi
    rm -f "$PID_FILE"
fi
echo $$ > "$PID_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Volt Watchdog Online. Grammy-Nominated Matrix Active..." | tee -a "$LOG_FILE"

while true; do
    for lead_file in "$LEADS_DIR"/*; do
        [ -f "$lead_file" ] && [[ "$lead_file" != *.processing ]] || continue

        filename=$(basename "$lead_file")
        artist_name="${filename%.*}"

        processing_file="$LEADS_DIR/${filename}.processing"
        mv "$lead_file" "$processing_file" 2>/dev/null

        if [ ! -f "$processing_file" ]; then
            continue
        fi

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Processing: $artist_name" | tee -a "$LOG_FILE"
        osascript -e "display notification \"Engineering Grammy-backed pitch for $artist_name...\" with title \"🏆 GRAMMY-NOMINATED VOLT\" sound name \"Glass\"" 2>/dev/null

        pitch_output=$(ollama run qwen3:14b "
        You are the elite booking closer for Volt Records in Atlanta, representing founder Mykel T. Brooks—a **Grammy Award-nominated** songwriter, producer, and 15-year music industry veteran.

        CRITICAL VALUE PROPS:
        1. Mykel T. Brooks is **Grammy Award-nominated**. This must be highlighted.
        2. EXCLUSIVE PROMOTION: We are giving new independent artists **1 FREE HOUR** of studio time to test the room and experience elite tracking risk-free.

        STUDIO PRICING (Apply the free hour discount to their requested session length):
        - A Room: \$90/hour (Neumann/Tube-Tech chains).
        - B Room: \$75/hour (Production & Mixing).

        INSTRUCTIONS:
        Analyze this lead:
        $(cat "$processing_file")

        Write a direct, hyper-compelling 2-3 sentence outreach pitch. Lead with the fact that a Grammy-nominated producer is giving them 1 free hour at Volt Records to hear their vocals on a major-label vocal chain. Show the calculated deal math with the 1 free hour subtracted from their expected time. Direct them to http://sqtheafterparty.base44.app/ to hear 'Toni Macaroni' as proof of the room's sonic weight. Keep the tone elite, confident, and direct.

        Format your output EXACTLY like this:
        ARTIST: $artist_name
        ROOM TARGET: [A Room or B Room]
        DEAL STRUCTURE: [Show math with the 1 Free Hour subtracted]
        PITCH:
        [Your pitch here]
        " 2>>"$LOG_FILE")

        if [ -z "$pitch_output" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Ollama returned empty output for $artist_name" | tee -a "$LOG_FILE"
            mv "$processing_file" "$LEADS_DIR/$filename"
            continue
        fi

        if ! echo "$pitch_output" | grep -q "^ARTIST:"; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: Output missing ARTIST tag for $artist_name. Saving raw output." | tee -a "$LOG_FILE"
            echo "$pitch_output" > "$PITCH_QUEUE/${artist_name}_pitch.txt"
        else
            echo "$pitch_output" | awk '/^ARTIST:/{flag=1} flag' > "$PITCH_QUEUE/${artist_name}_pitch.txt"
        fi

        mv "$processing_file" "$CLOSED_DIR/$filename"

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Pitch saved: $PITCH_QUEUE/${artist_name}_pitch.txt" | tee -a "$LOG_FILE"
        osascript -e "display notification \"Grammy-tier pitch ready for $artist_name!\" with title \"💰 ROSTER EXPANDED\" sound name \"Submarine\"" 2>/dev/null
    done
    sleep "$SLEEP_INTERVAL"
done
