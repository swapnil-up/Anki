#!/bin/bash

# Directory containing the .txt files
INPUT_DIR="."

# Iterate over each .txt file in the directory
for INPUT_FILE in "$INPUT_DIR"/*.txt; do
    # Get the base name of the file (without extension) for the output CSV
    BASE_NAME=$(basename "$INPUT_FILE" .txt)
    OUTPUT_FILE="${BASE_NAME}.csv"

    echo "Processing file: $INPUT_FILE"

    # Initialize the output file and add the header
    echo "Quote|Added On" > "$OUTPUT_FILE"

    # Initialize variables
    quote=""
    added_on=""

    # Read the input file line by line
    while IFS= read -r line; do
        # Check for the start of a new highlight entry
        if [[ $line == -* ]]; then
            # If there's an ongoing quote, save it before starting a new entry
            if [[ ! -z $quote ]]; then
                echo "\"$quote\"|\"$added_on\"" >> "$OUTPUT_FILE"
                quote=""
            fi
            # Extract the datetime
            added_on=$(echo "$line" | grep -oP 'Added on \K.*')
        elif [[ $line == *=* ]]; then
            # Do nothing for separator lines
            continue
        elif [[ -z $line ]]; then
            # If the line is empty, it's the end of a quote block
            if [[ ! -z $quote ]]; then
                # Save the accumulated quote and added_on to the CSV file
                echo "\"$quote\"|\"$added_on\"" >> "$OUTPUT_FILE"
                # Reset the quote variable
                quote=""
            fi
        else
            # Accumulate the quote text, replacing any embedded quotes
            if [[ -z $quote ]]; then
                quote=$(echo "$line" | sed 's/"/""/g')
            else
                quote="$quote $(echo "$line" | sed 's/"/""/g')"
            fi
        fi
    done < "$INPUT_FILE"

    # If there's a quote left at the end, write it to the CSV
    if [[ ! -z $quote ]]; then
        echo "\"$quote\"|\"$added_on\"" >> "$OUTPUT_FILE"
    fi

    echo "CSV file created successfully: $OUTPUT_FILE"
done

echo "All files processed."

