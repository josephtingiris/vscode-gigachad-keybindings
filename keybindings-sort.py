#!/usr/bin/env python3
"""
(C) 2026 Joseph Tingiris (joseph.tingiris@gmail.com)

Usage:

python3 keybindings-sort.py [--primary {key,when}] < keybindings.json

Examples:

python3 keybindings-sort.py < keybindings.json > keybindings.sorted.json
python3 keybindings-sort.py --primary when < keybindings.json > keybindings.sorted.by_when.json
python3 keybindings-sort.py --primary when < keybindings.json > keybindings.sorted.json ; /bin/cp -f keybindings.sorted.json keybindings.json # in place

Description:

Sorts a VS Code `keybindings.json` (JSONC) array. By default the script sorts by
`key` (natural order), then by `when` (natural order), and finally by `_comment` if
present. Pass `--primary when` (or `-p when`) to make `when` the primary sort key
(then `key`, then `_comment`). Both `key` and `when` use natural ordering so numeric
segments sort intuitively (e.g. "ctrl+2" before "ctrl+10").

Preserves comments and surrounding formatting:
- before the opening `[` of the array
- after the closing `]` of the array
- inside and around each `{ ... }` object in the array

Behavior notes:
- Attempts to preserve trailing commas and existing object comments.
- Annotates objects that are exact duplicates (same `key` and `when`) with a
    trailing `// DUPLICATE` comment.
"""
import sys
import re
import json
import argparse
from typing import List, Tuple

def extract_preamble_postamble(text):
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1 or end < start:
        return '', '', text
    preamble = text[:start]
    postamble = text[end+1:]
    array_text = text[start+1:end]  # exclude [ and ]
    return preamble, array_text, postamble

def group_objects_with_comments(array_text: str) -> Tuple[List[Tuple[str, str]], str]:
    groups = []
    comments = ''
    buf = ''
    depth = 0
    in_obj = False
    for line in array_text.splitlines(keepends=True):
        stripped = line.strip()
        if not in_obj:
            if '{' in stripped:
                in_obj = True
                depth = stripped.count('{') - stripped.count('}')
                buf = line
            else:
                comments += line
        else:
            buf += line
            depth += line.count('{') - line.count('}')
            if depth == 0:
                groups.append((comments, buf))
                comments = ''
                buf = ''
                in_obj = False
    trailing_comments = comments
    return groups, trailing_comments

def strip_json_comments(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return ''
        return s
    pattern = r'("(?:\\.|[^"\\])*"|//.*?$|/\*.*?\*/)'  # string or comment
    return re.sub(pattern, replacer, text, flags=re.DOTALL | re.MULTILINE)

def strip_trailing_commas(text):
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text

def natural_key(s):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def extract_sort_keys(obj_text: str, primary: str = 'key') -> Tuple:
    obj_match = re.search(r'\{.*\}', obj_text, re.DOTALL)
    if not obj_match:
        return ([], '', '')
    obj_str = obj_match.group(0)
    try:
        clean = strip_json_comments(obj_str)
        clean = strip_trailing_commas(clean)
        obj = json.loads(clean)
        key_val = str(obj.get('key', ''))
        when_val = str(obj.get('when', ''))
        comment_val = str(obj.get('_comment', ''))
        # Support alternate primary sort order. Use natural order for both
        # `key` and `when` values so numeric segments sort naturally.
        if primary == 'when':
            return (natural_key(when_val), natural_key(key_val), comment_val)
        else:
            return (natural_key(key_val), natural_key(when_val), comment_val)
    except Exception:
        return ([], '', '')

def extract_key_when(obj_text: str) -> Tuple[str, str]:
    obj_match = re.search(r'\{.*\}', obj_text, re.DOTALL)
    if not obj_match:
        return ('', '')
    obj_str = obj_match.group(0)
    try:
        clean = strip_json_comments(obj_str)
        clean = strip_trailing_commas(clean)
        obj = json.loads(clean)
        key_val = str(obj.get('key', ''))
        when_val = str(obj.get('when', ''))
        return (key_val, when_val)
    except Exception:
        return ('', '')

def object_has_trailing_comma(obj_text: str) -> bool:
    lines = obj_text.rstrip().splitlines()
    found_closing = False
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if not found_closing and stripped.endswith('}'):  # first closing brace
            found_closing = True
            continue
        if found_closing:
            # Only allow whitespace or comments after closing brace
            if stripped.startswith(','):
                return True
            elif stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                return False
    return False

def main():
    parser = argparse.ArgumentParser(description='Sort VS Code keybindings.json by key/when')
    parser.add_argument('--primary', '-p', choices=['key', 'when'], default='key',
                        help="Primary sort field: 'key' (default) or 'when'")
    args = parser.parse_args()

    primary_order = args.primary

    raw = sys.stdin.read()
    preamble, array_text, postamble = extract_preamble_postamble(raw)
    groups, trailing_comments = group_objects_with_comments(array_text)
    # Sort by chosen primary (natural), then the other field (natural), then by _comment
    sorted_groups = sorted(groups, key=lambda pair: extract_sort_keys(pair[1], primary=primary_order))
    seen = set()
    sys.stdout.write(preamble)
    sys.stdout.write('[')
    for i, (comments, obj) in enumerate(sorted_groups):
        is_last = (i == len(sorted_groups) - 1)
        key_val, when_val = extract_key_when(obj)
        pair_id = (key_val, when_val)
        # Annotate if duplicate
        if pair_id in seen:
            comments += f'// DUPLICATE key: {key_val!r} when: {when_val!r}\n'
        seen.add(pair_id)
        sys.stdout.write(comments)
        obj_out = obj.rstrip()
        idx = obj_out.rfind('}')
        if idx != -1:
            after = obj_out[idx+1:]
            after_clean = re.sub(r'^\s*,+', '', after)
            obj_out = obj_out[:idx+1] + after_clean
        sys.stdout.write(obj_out)
        if not is_last and not object_has_trailing_comma(obj_out):
            sys.stdout.write(',')
        sys.stdout.write('\n')
    sys.stdout.write(trailing_comments)
    sys.stdout.write(']')
    sys.stdout.write(postamble)
    if not postamble.endswith('\n'):
        sys.stdout.write('\n')

if __name__ == "__main__":
    main()
