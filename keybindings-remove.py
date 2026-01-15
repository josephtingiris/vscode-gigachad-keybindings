#!/usr/bin/env python3
"""
(C) 2026 Joseph Tingiris (joseph.tingiris@gmail.com)

Usage:

python3 keybindings-remove.py <attribute> <search_string> < keybindings.json

Examples:

python3 keybindings-remove.py _gigachad gigachad < keybindings.json > keybindings-nogigachad.json

Description:

Removes objects from a VS Code `keybindings.json` array when the given
attribute's value contains the provided search string (substring, case-sensitive).
The entire object is removed (and its trailing comma handled) while preserving
comments and surrounding formatting.

Preserves JSONC comments and surrounding formatting:
- before the opening `[` of the array
- after the closing `]` of the array
- inside and around each `{ ... }` object in the array

Behavior notes:
- Outputs the modified JSONC to stdout.
- Use the environment variable `KEYBINDINGS_REMOVE_DEBUG=1` to enable debug
    logging to stderr when JSON parsing or matches occur.
"""
import sys
import os
import re
import json

def extract_preamble_postamble(text):
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1 or end < start:
        return '', '', text
    preamble = text[:start]
    postamble = text[end+1:]
    array_text = text[start+1:end]  # exclude [ and ]
    return preamble, array_text, postamble

def split_units(array_text: str):
    # Each unit: (comments/whitespace before, object, trailing comma, whitespace)
    units = []
    lines = array_text.splitlines(keepends=True)
    i = 0
    n = len(lines)
    while i < n:
        comments = ''
        # Gather comments/whitespace before object
        while i < n and '{' not in lines[i]:
            comments += lines[i]
            i += 1
        if i >= n:
            break
        # Gather object
        obj_lines = ''
        depth = 0
        started = False
        while i < n:
            line = lines[i]
            if '{' in line:
                started = True
                depth += line.count('{')
            if started:
                obj_lines += line
            if '}' in line:
                depth -= line.count('}')
                if depth == 0:
                    i += 1
                    break
            i += 1
        # Gather trailing comma and whitespace
        trailing = ''
        while i < n and (lines[i].strip().startswith(',') or lines[i].strip() == '' or lines[i].strip().startswith('//') or lines[i].strip().startswith('/*')):
            trailing += lines[i]
            i += 1
        units.append((comments, obj_lines, trailing))
    return units

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

def should_remove(obj_text, attr, val):
    # non-greedy match to extract the JSON object body
    obj_match = re.search(r'\{[\s\S]*?\}', obj_text)
    if not obj_match:
        return False
    obj_str = obj_match.group(0)
    try:
        clean = strip_json_comments(obj_str)
        clean = strip_trailing_commas(clean)
        obj = json.loads(clean)
        # perform substring check (case-sensitive)
        attr_val = obj.get(attr, '')
        contains = val in str(attr_val)
        # debug output to stderr when KEYBINDINGS_REMOVE_DEBUG env var set
        if os.environ.get('KEYBINDINGS_REMOVE_DEBUG'):
            print('DEBUG: obj=', obj, file=sys.stderr)
            print(f"DEBUG: attr={attr!r} attr_val={attr_val!r} contains={contains}", file=sys.stderr)
        return contains
    except Exception:
        # Debug info when parsing fails
        if os.environ.get('KEYBINDINGS_REMOVE_DEBUG'):
            print(f"DEBUG: failed to parse object text: {obj_str}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 keybindings-remove.py <attribute> <search_string>", file=sys.stderr)
        sys.exit(1)
    attr, val = sys.argv[1], sys.argv[2]
    raw = sys.stdin.read()
    preamble, array_text, postamble = extract_preamble_postamble(raw)
    units = split_units(array_text)
    # Output
    sys.stdout.write(preamble)
    sys.stdout.write('[')
    for comments, obj, trailing in units:
        if should_remove(obj, attr, val):
            continue
        sys.stdout.write(comments)
        sys.stdout.write(obj)
        sys.stdout.write(trailing)
    sys.stdout.write(']')
    sys.stdout.write(postamble)
    if not postamble.endswith('\n'):
        sys.stdout.write('\n')

if __name__ == "__main__":
    main()
