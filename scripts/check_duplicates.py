import json
from collections import Counter, defaultdict

def analyze_duplicates(file_path, key_field):
    """Analyze duplicates in a JSONL file"""
    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                entry = json.loads(line)
                entries.append((line_num, entry))
    
    # Count occurrences of each key
    key_counts = Counter(entry[key_field] for _, entry in entries)
    
    # Find duplicates
    duplicates = {k: v for k, v in key_counts.items() if v > 1}
    
    print(f"\n{'='*80}")
    print(f"File: {file_path}")
    print(f"{'='*80}")
    print(f"Total entries: {len(entries)}")
    print(f"Unique {key_field}s: {len(key_counts)}")
    print(f"Duplicate {key_field}s: {len(duplicates)}")
    
    if duplicates:
        print(f"\nDuplicate {key_field}s found:")
        for key, count in duplicates.items():
            print(f"  - {key}: appears {count} times")
            # Show line numbers where this key appears
            lines = [line_num for line_num, entry in entries if entry[key_field] == key]
            print(f"    Lines: {lines}")
    
    return entries, duplicates

def analyze_actions_with_source_screen():
    """Analyze actions.jsonl for source_screen_id issues"""
    file_path = r"d:\4\thesis\lab\agent\web-agent\data\raw\agenttrek\actions.jsonl"
    
    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                entry = json.loads(line)
                entries.append((line_num, entry))
    
    print(f"\n{'='*80}")
    print(f"Actions source_screen_id Analysis")
    print(f"{'='*80}")
    
    # Group by source_screen_id
    by_source = defaultdict(list)
    for line_num, entry in entries:
        source = entry.get('source_screen_id', '')
        by_source[source].append((line_num, entry['action_id']))
    
    print(f"\nActions without source_screen_id (empty string): {len(by_source[''])}")
    if by_source['']:
        print("  Actions:")
        for line_num, action_id in by_source[''][:10]:  # Show first 10
            print(f"    Line {line_num}: {action_id}")
        if len(by_source['']) > 10:
            print(f"    ... and {len(by_source['']) - 10} more")
    
    print(f"\nActions WITH source_screen_id: {sum(len(v) for k, v in by_source.items() if k != '')}")
    for source_id, actions in by_source.items():
        if source_id:
            print(f"  {source_id}: {len(actions)} actions")
    
    # Check for action_id duplicates
    action_id_counts = Counter(entry['action_id'] for _, entry in entries)
    duplicates = {k: v for k, v in action_id_counts.items() if v > 1}
    
    print(f"\nDuplicate action_ids: {len(duplicates)}")
    if duplicates:
        for action_id, count in list(duplicates.items())[:10]:  # Show first 10
            print(f"  {action_id}: {count} times")
            lines = [line_num for line_num, entry in entries if entry['action_id'] == action_id]
            print(f"    Lines: {lines}")

# Analyze screens
print("\n" + "="*80)
print("DUPLICATE ANALYSIS")
print("="*80)

screens_path = r"d:\4\thesis\lab\agent\web-agent\data\raw\agenttrek\screens.jsonl"
actions_path = r"d:\4\thesis\lab\agent\web-agent\data\raw\agenttrek\actions.jsonl"

screens, screens_dups = analyze_duplicates(screens_path, 'screen_id')
actions, actions_dups = analyze_duplicates(actions_path, 'action_id')

# Analyze actions with source_screen_id
analyze_actions_with_source_screen()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"screens.jsonl: {len(screens)} total, {len(screens_dups)} duplicate screen_ids")
print(f"actions.jsonl: {len(actions)} total, {len(actions_dups)} duplicate action_ids")
