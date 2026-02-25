#!/usr/bin/env python3
"""
Deduplicate JSONL files by removing duplicate entries.

For screens.jsonl: Keep only unique screen_id (last occurrence)
For actions.jsonl: Keep only unique action_id (last occurrence with most data)
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any


def deduplicate_jsonl(
    input_file: Path,
    output_file: Path,
    key_field: str,
    prefer_last: bool = True
) -> tuple[int, int]:
    """
    Deduplicate a JSONL file based on a key field.
    
    Args:
        input_file: Input JSONL file path
        output_file: Output JSONL file path
        key_field: Field to use as unique key
        prefer_last: If True, keep last occurrence; else keep first
        
    Returns:
        Tuple of (original_count, deduplicated_count)
    """
    entries: Dict[str, Dict[str, Any]] = {}
    original_count = 0
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            original_count += 1
            entry = json.loads(line)
            key = entry[key_field]
            
            if prefer_last:
                # Always overwrite with latest
                entries[key] = entry
            else:
                # Keep first occurrence
                if key not in entries:
                    entries[key] = entry
    
    deduplicated_count = len(entries)
    
    print(f"Writing {deduplicated_count} unique entries to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entries.values():
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"Done! {original_count} → {deduplicated_count} "
          f"({original_count - deduplicated_count} duplicates removed)")
    
    return original_count, deduplicated_count


def deduplicate_actions_smart(input_file: Path, output_file: Path) -> tuple[int, int]:
    """
    Smart deduplication for actions: prefer entries with more complete data.
    
    For actions, we want to keep the version with:
    1. Non-empty source_screen_id (if available)
    2. Higher confidence
    3. Executable status = 'executed' > 'pending'
    """
    entries: Dict[str, Dict[str, Any]] = {}
    original_count = 0
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            original_count += 1
            entry = json.loads(line)
            action_id = entry['action_id']
            
            # If we haven't seen this action_id, add it
            if action_id not in entries:
                entries[action_id] = entry
                continue
            
            # Compare and keep the better version
            existing = entries[action_id]
            
            # Prefer executed over pending
            existing_status = existing.get('meta', {}).get('executable_status', 'pending')
            new_status = entry.get('meta', {}).get('executable_status', 'pending')
            
            if new_status == 'executed' and existing_status != 'executed':
                entries[action_id] = entry
                continue
            
            # If both executed or both pending, prefer one with source_screen_id
            existing_source = existing.get('source_screen_id', '')
            new_source = entry.get('source_screen_id', '')
            
            if new_source and not existing_source:
                entries[action_id] = entry
                continue
            
            # If tied, keep higher confidence
            if entry.get('confidence', 0) > existing.get('confidence', 0):
                entries[action_id] = entry
    
    deduplicated_count = len(entries)
    
    print(f"Writing {deduplicated_count} unique entries to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entries.values():
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"Done! {original_count} → {deduplicated_count} "
          f"({original_count - deduplicated_count} duplicates removed)")
    
    return original_count, deduplicated_count


def main():
    parser = argparse.ArgumentParser(description='Deduplicate JSONL files')
    parser.add_argument('--dir', type=str, 
                       default=r'data\raw\agenttrek',
                       help='Directory containing JSONL files')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup files (.bak) before deduplicating')
    
    args = parser.parse_args()
    
    base_dir = Path(args.dir)
    
    if not base_dir.exists():
        print(f"Error: Directory {base_dir} does not exist")
        return 1
    
    screens_file = base_dir / 'screens.jsonl'
    actions_file = base_dir / 'actions.jsonl'
    
    # Backup if requested
    if args.backup:
        print("Creating backups...")
        if screens_file.exists():
            screens_file.rename(base_dir / 'screens.jsonl.bak')
            screens_file = base_dir / 'screens.jsonl.bak'
        if actions_file.exists():
            actions_file.rename(base_dir / 'actions.jsonl.bak')
            actions_file = base_dir / 'actions.jsonl.bak'
    
    print("\n" + "=" * 80)
    print("DEDUPLICATING DATA")
    print("=" * 80)
    
    # Deduplicate screens
    if screens_file.exists():
        print("\nScreens:")
        output_screens = base_dir / 'screens.jsonl'
        deduplicate_jsonl(screens_file, output_screens, 'screen_id', prefer_last=True)
    else:
        print(f"\nWarning: {screens_file} not found")
    
    # Deduplicate actions (smart)
    if actions_file.exists():
        print("\nActions (smart deduplication):")
        output_actions = base_dir / 'actions.jsonl'
        deduplicate_actions_smart(actions_file, output_actions)
    else:
        print(f"\nWarning: {actions_file} not found")
    
    print("\n" + "=" * 80)
    print("DEDUPLICATION COMPLETE")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    exit(main())
