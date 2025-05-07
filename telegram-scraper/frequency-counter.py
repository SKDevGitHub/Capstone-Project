import json
import os
import re
from collections import Counter

def extract_ticker_name(message):
    """
    Extracts a potential ticker name from a message string for the COUNTING phase.

    Assumes the ticker name is the text between an optional leading symbol/emoji
    and the first '|' character on the first line. Handles potential variations.
    Returns the ticker in lowercase. This is used when searching OTHER files.

    Args:
        message (str): The message string to parse.

    Returns:
        str or None: The extracted ticker name (stripped of whitespace and lowercased),
                     or None if no match is found or input is invalid.
    """
    if not isinstance(message, str):
        return None

    first_line = message.split('\n', 1)[0]
    # Regex explanation (for general matching in other files):
    # ^             - Start of the string (first line)
    # (?:.*\s)?    - Optional non-capturing group for leading symbols/emojis + space
    # ([^|]+?)     - Capturing group 1: Ticker name (one or more non-pipe chars, non-greedy)
    # \s*\|.* - Whitespace, literal '|', rest of the line
    match = re.match(r'^(?:.*\s)?([^|]+?)\s*\|.*', first_line, re.IGNORECASE)
    if match:
        return match.group(1).strip().lower()

    # Simpler pattern (no leading symbol)
    match_simple = re.match(r'^([^|]+?)\s*\|.*', first_line, re.IGNORECASE)
    if match_simple:
        return match_simple.group(1).strip().lower()

    # Fallback (heuristic, might need adjustment)
    fallback_match = re.match(r'^([\w\s]+)(?:\n|:|$)', message)
    if fallback_match:
        potential_ticker = fallback_match.group(1).strip()
        if potential_ticker and len(potential_ticker) < 30 and not potential_ticker.isdigit():
            return potential_ticker.lower()

    return None

def extract_tickers_from_source(source_file_path):
    """
    Reads the specific source JSON file and extracts ticker names that appear
    AFTER the '🔔' emoji and BEFORE the first '|' on the first line.

    Args:
        source_file_path (str): The full path to the source JSON file.

    Returns:
        set: A set of unique ticker names (lowercase) found in the source file
             matching the specific '🔔 Name |' pattern. Returns an empty set
             if the file is not found, invalid, or contains no matching tickers.
    """
    target_tickers = set()
    print(f"Attempting to extract target tickers from source: {source_file_path}")
    print("Using specific pattern: Starts with '🔔', text before '|'")

    if not os.path.isfile(source_file_path):
        print(f"  Error: Source file not found: {source_file_path}")
        return target_tickers

    # Define the specific regex pattern for the source file
    # ^🔔      - Starts with the bell emoji
    # \s* - Optional whitespace
    # ([^|]+?) - Capture group 1: Ticker name (one or more non-pipe chars, non-greedy)
    # \s* - Optional whitespace
    # \|        - Literal pipe symbol
    # .* - Rest of the line
    source_pattern = re.compile(r'^🔔\s*([^|]+?)\s*\|.*')
    try:
        with open(source_file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"  Warning: Invalid JSON format in source file: {source_file_path}. Skipping.")
                return target_tickers

            if not isinstance(data, list):
                 if isinstance(data, dict): data = [data] # Handle single object case
                 else:
                    print(f"  Warning: Source file does not contain a list of objects: {source_file_path}. Skipping.")
                    return target_tickers

            # Process entries specifically for the source file format
            for entry in data:
                if isinstance(entry, dict) and 'message' in entry:
                    message_content = entry.get('message')
                    if isinstance(message_content, str):
                        first_line = message_content.split('\n', 1)[0]
                        match = source_pattern.match(first_line)
                        if match:
                            ticker = match.group(1).strip().lower()
                            if ticker: # Ensure ticker is not empty after stripping
                                target_tickers.add(ticker)

        print(f"  Successfully extracted {len(target_tickers)} unique target tickers matching the specific pattern from source file.")

    except Exception as e:
        print(f"  Error: An unexpected error occurred while processing source file {source_file_path}: {e}")

    return target_tickers
  
def count_target_tickers_recursive(root_directory, target_tickers, source_file_path_to_exclude):
    """
    Recursively analyzes JSON files (excluding the source file) in a directory
    and counts occurrences of the pre-defined target tickers using the general
    extraction logic (`extract_ticker_name`).

    Args:
        root_directory (str): The path to the root directory to start searching from.
        target_tickers (set): A set of lowercase ticker names to count.
        source_file_path_to_exclude (str): The absolute path of the source file to skip during counting.

    Returns:
        collections.Counter: A Counter object with target tickers as keys
                             and their counts as values across all other JSON files.
    """
    if not target_tickers:
        print("No target tickers provided. Skipping count phase.")
        return Counter()

    if not os.path.isdir(root_directory):
        print(f"Error: Root directory for counting not found: {root_directory}")
        return Counter()

    # Initialize counts for all target tickers to 0
    ticker_counts = Counter({ticker: 0 for ticker in target_tickers})
    processed_files = 0
    processed_entries = 0
    found_target_occurrences = 0

    print(f"\nStarting count phase in root directory: {root_directory}")
    print(f"Searching for occurrences of {len(target_tickers)} target tickers (using general extraction)...")
    print(f"Excluding source file: {source_file_path_to_exclude}")
  
    # Normalize the path to exclude for reliable comparison
    normalized_exclude_path = os.path.normpath(source_file_path_to_exclude)

    for dirpath, dirnames, filenames in os.walk(root_directory):
        # Optional: Add print statement here if needed for debugging directory traversal
        # print(f"\nSearching in: {dirpath}")
        json_files_in_dir = [f for f in filenames if f.lower().endswith(".json")]

        # Removed the 'no JSON files found' print statement for cleaner output unless debugging

        for filename in json_files_in_dir:
            file_path = os.path.join(dirpath, filename)
            normalized_file_path = os.path.normpath(file_path)

            # *** Skip the source file ***
            if normalized_file_path == normalized_exclude_path:
                # print(f"  Skipping source file: {filename}") # Keep this commented unless debugging
                continue

            # print(f"  Processing file for counts: {filename}...") # Keep commented for cleaner output
            file_occurrences_found = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # print(f"    Warning: Skipping {filename} - Invalid JSON format or empty file.")
                        continue # Silently skip invalid JSON during counting
                    if not isinstance(data, list):
                        if isinstance(data, dict): data = [data] # Handle single object case
                        else:
                            # print(f"    Warning: Skipping {filename} - Expected list or object, found {type(data)}.")
                            continue # Silently skip unexpected data types

                    # Use the general extract_ticker_name here for counting
                    for entry in data:
                        processed_entries += 1
                        if isinstance(entry, dict) and 'message' in entry:
                            message_content = entry.get('message')
                            # Extract potential ticker from this message using general method
                            ticker_in_message = extract_ticker_name(message_content)
                            # Check if it's one of the target tickers we're looking for
                            if ticker_in_message and ticker_in_message in target_tickers:
                                ticker_counts[ticker_in_message] += 1
                                found_target_occurrences += 1
                                file_occurrences_found +=1

                processed_files += 1
                # print(f"    Finished processing {filename}. Found {file_occurrences_found} occurrences of target tickers.") # Keep commented

            except FileNotFoundError:
                print(f"    Error: File not found (unexpected with os.walk): {filename}")
            except Exception as e:
                print(f"    Error: An unexpected error occurred while processing {filename}: {e}")

    print(f"\n--- Count Phase Complete ---")
    if processed_files == 0:
        print("No other JSON files were found or processed for counting.")
    else:
        print(f"Processed {processed_files} JSON file(s) (excluding source).")
        print(f"Checked {processed_entries} total entries in these files.")
        print(f"Found {found_target_occurrences} total occurrences of the target tickers.")

    return ticker_counts
if __name__ == "__main__":
    # Get the directory where the script is located
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # --- Step 1: Extract Target Tickers from the specific source file ---
    # Define the relative path to the source file from the script's directory
    source_sub_dir = "TheDegenBoysLounge"
    source_filename = "TheDegenBoysLounge.json"
    source_file_full_path = os.path.join(script_directory, source_sub_dir, source_filename)

    # Extract tickers using the refined logic for the source file
    target_tickers_set = extract_tickers_from_source(source_file_full_path)

    # --- Step 2: Count occurrences of target tickers in all other JSON files ---
    if target_tickers_set: # Only proceed if we found tickers in the source file
        # Count occurrences using the general extraction logic in other files
        results = count_target_tickers_recursive(script_directory, target_tickers_set, source_file_full_path)

        # --- Step 3: Print the results ---
        print("\n--- Final Ticker Counts (from source file, counted in others) ---")
        if results:
            # Sort results by count descending for better readability
            for ticker, count in results.most_common():
                print(f"{ticker}: {count}")
        else:
                 # This case means target tickers were found, but zero occurrences in other files
            print("No occurrences of the target tickers were found in any other JSON files.")
            # Optionally print the list of tickers that were searched for:
            # print("\nTickers searched for:")
            # for ticker in sorted(list(target_tickers_set)):
            #    print(f"- {ticker}")


    else:
        # This case means the source file extraction yielded no tickers matching the pattern
        print("\nNo target tickers matching the '🔔 Name |' pattern were extracted from the source file. Cannot perform count.")