#!/bin/bash

# Define hidden log file
LOG_FILE=~/.anki_debug.log

# Clear previous log
echo "Starting script..." > "$LOG_FILE"

# Check if Anki is running
if ! pgrep -x "anki" > /dev/null; then
    echo "Anki is not running. Launching Anki..." >> "$LOG_FILE"
    anki &
    # Wait for a few seconds to ensure Anki is up and running
    sleep 10
fi

# Get highlighted text
highlighted_text=$(xclip -o)
echo "Highlighted text: $highlighted_text" >> "$LOG_FILE"

# Get the current date and time
current_datetime=$(date '+%Y-%m-%d %H:%M:%S')
echo "Current date and time: $current_datetime" >> "$LOG_FILE"

# Get the active window ID immediately after getting the highlighted text
active_window_id=$(xdotool getactivewindow)
echo "Active window ID: $active_window_id" >> "$LOG_FILE"

# Get the window class name
window_class=$(xprop -id "$active_window_id" | grep "WM_CLASS(STRING)" | awk -F'"' '{print $4}')
echo "Window class: $window_class" >> "$LOG_FILE"

# Capture all window properties for debugging
echo "Full xprop output for debugging:" >> "$LOG_FILE"
xprop -id "$active_window_id" >> "$LOG_FILE"

# Determine the source based on the window class
if [ "$window_class" == "google-chrome" ] || [ "$window_class" == "firefox" ]; then
    source=$(xdotool getwindowfocus getwindowname)
elif [ "$window_class" == "calibre-ebook-viewer" ] || [ "$window_class" == "calibre" ]; then
    # Try capturing different window properties for Calibre
    source=$(xprop -id "$active_window_id" | grep "_NET_WM_NAME(UTF8_STRING)" | cut -d'"' -f2)
elif [ "$window_class" == "evince" ] || [ "$window_class" == "Evince" ]; then
    # Capture the window name for Evince
    source=$(xprop -id "$active_window_id" | grep -e "_NET_WM_NAME(UTF8_STRING)" -e "WM_NAME(COMPOUND_TEXT)" | grep -o '".*"' | sed 's/"//g')
else
    source=$(xprop -id "$active_window_id" | grep "WM_NAME(STRING)" | awk -F'"' '{print $2}')
fi
echo "Detected window class: $window_class" >> "$LOG_FILE"
echo "Source: $source" >> "$LOG_FILE"

# Replace with your Anki deck name
DECK_NAME="Testing"

# Replace with your Anki note type (for cloze deletions)
NOTE_TYPE="Cloze"

# JSON payload to add the card using guiAddCards
payload=$(jq -n \
  --arg deck "$DECK_NAME" \
  --arg note "$NOTE_TYPE" \
  --arg text "$highlighted_text" \
  --arg extra "$current_datetime\nSource: $source" \
  '{
    "action": "guiAddCards",
    "version": 6,
    "params": {
      "note": {
        "deckName": $deck,
        "modelName": $note,
        "fields": {
          "Text": $text,
          "Extra": $extra
        },
        "tags": []
      }
    }
  }')
echo "Payload: $payload" >> "$LOG_FILE"

# Send request to AnkiConnect
response=$(curl -s -X POST -d "$payload" http://localhost:8765)
echo "Response: $response" >> "$LOG_FILE"

# Check response and log detailed info
if echo "$response" | grep -q '"error":null'; then
    echo "Card added successfully!" >> "$LOG_FILE"
    echo "Please manually confirm and close the Add Cards dialog in Anki." >> "$LOG_FILE"
else
    echo "Failed to add card." >> "$LOG_FILE"
    echo "Payload sent to AnkiConnect: $payload" >> "$LOG_FILE"
    echo "Response from AnkiConnect: $response" >> "$LOG_FILE"
fi

