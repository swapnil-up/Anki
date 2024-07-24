#!/bin/bash

# Define log file
LOG_FILE=~/anki_debug.log

# Clear previous log
echo "Starting script..." > "$LOG_FILE"

# Check if Anki is running
if ! pgrep -x "anki" > /dev/null
then
    echo "Anki is not running. Launching Anki..."
    anki &
    # Wait for a few seconds to ensure Anki is up and running
    sleep 10
fi

# Get highlighted text
highlighted_text=$(xclip -o)
echo "Highlighted text: $highlighted_text" >> "$LOG_FILE"

# Replace with your Anki deck name
DECK_NAME="Testing"

# Replace with your Anki note type (for cloze deletions)
NOTE_TYPE="Cloze"

# Use zenity to get edited text from the user
edited_text=$(zenity --text-info --editable --title="Edit Note" --filename=/dev/stdin <<< "$highlighted_text")

# Check if zenity was closed without saving
if [ $? -ne 0 ]; then
  echo "Zenity was closed without saving. Exiting..."
  exit 1
fi

echo "Edited text: $edited_text" >> "$LOG_FILE"

# JSON payload to add the card
payload=$(jq -n \
  --arg deck "$DECK_NAME" \
  --arg note "$NOTE_TYPE" \
  --arg text "$edited_text" \
  '{
    "action": "addNote",
    "version": 6,
    "params": {
      "note": {
        "deckName": $deck,
        "modelName": $note,
        "fields": {
          "Text": $text
        },
        "tags": []
      }
    }
  }')
echo "Payload: $payload" >> "$LOG_FILE"

# Send request to AnkiConnect
response=$(curl -s -X POST -d "$payload" http://localhost:8765)
echo "Response: $response" >> "$LOG_FILE"

# Check response
if echo "$response" | grep -q '"error":null'; then
  echo "Card added successfully!"
else
  echo "Failed to add card."
fi
