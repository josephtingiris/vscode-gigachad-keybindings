#!/usr/bin/env python3
"""
(C) 2026 Joseph Tingiris (joseph.tingiris@gmail.com)

Usage:

python3 keybindings-gigachad.py [LEFT_KEY] [RIGHT_KEY] > keybindings.json

Examples:

python3 keybindings-gigachad.py > keybindings_gigachad.json
python3 keybindings-gigachad.py ctrl h

Description:

Generates VS Code `keybindings.json` like ouput containing permutations of left-hand
modifier keys, right-hand keys, focused conditions, and visible conditions. By default
the script uses the built-in `LEFT_HAND_KEYS`, `RIGHT_HAND_KEYS`, `WHEN_FOCUSED`, and
`WHEN_VISIBLE` arrays. If the first CLI argument matches a value in `LEFT_HAND_KEYS`,
only that left key is used; if the second CLI argument matches a value in
`RIGHT_HAND_KEYS`, only that right key is used.

For each `WHEN_FOCUSED` value the script includes every combination of
`WHEN_VISIBLE` (including none). Each generated binding contains a `_gigachad`
identifier, `key`, `command`, and `when` properties. The script prints the JSONC
to stdout and a trailing comment with the total count.

Behavior notes:
- Arrow-like right-hand keys enable an additional `config.gigachad.arrows`
    condition in the generated `when` expression, so arrows can resume default
    VS Code behavior.
- A timestamp is embedded in each `_gigachad` id to keep IDs unique.
- The generated `when` expressions include a `config.gigachad.enabled` condition to
    allow toggling the entire Gigachad keybinding set on or off via a user setting.
- VS Code can change Appearance settings per profile.  The current output of this
    script produces keybindings for the 'default' VS Code layout:
        - Primary Side Bar is on the left.
        - Panel is at the bottom.

TODO:
    - Add keybindings for when the Primary Side Bar is on the right vs left.
    - Disable Panel related keybindings for when it's in 'docked' mode or *not* on the bottom.
"""
import json
import itertools
import sys
from datetime import datetime

LEFT_HAND_KEYS = [
    "alt", "alt+shift", "ctrl", "ctrl+alt", "ctrl+shift", "ctrl+shift+alt", "shift"
]
RIGHT_HAND_KEYS = [
    "h", "left", "j", "down", "k", "up", "l", "right", "+", "=", "-", "_", "[", "]", "{", "}", "pageup", "pagedown"
]
WHEN_FOCUSED = [
    "sideBarFocus", "editorFocus", "panelFocus", "auxiliaryBarFocus"
]
WHEN_VISIBLE = [
    "sideBarVisible", "editorIsOpen", "panelVisible", "auxiliaryBarVisible"
]

ARROW_KEYS = {"left", "down", "up", "right", "pageup", "pagedown"}

dt_str = datetime.now().strftime("%y%m%d%H%M%S")

args = sys.argv[1:]
left_keys = LEFT_HAND_KEYS
right_keys = RIGHT_HAND_KEYS
if len(args) >= 1 and args[0] in LEFT_HAND_KEYS:
    left_keys = [args[0]]
if len(args) >= 2 and args[1] in RIGHT_HAND_KEYS:
    right_keys = [args[1]]

keybindings = []
for left, right, when_focused in itertools.product(left_keys, right_keys, WHEN_FOCUSED):
    # For each WHEN_FOCUSED, include all combinations of WHEN_VISIBLE (including none)
    visible_permutations = [[]]
    for n in range(1, len(WHEN_VISIBLE)+1):
        visible_permutations.extend(itertools.combinations(WHEN_VISIBLE, n))
    for visible_combo in visible_permutations:
        when_parts = [when_focused] + list(visible_combo)
        when_str = ' && '.join(when_parts)

        prefix = "config.gigachad.enabled"
        prefix += f" && config.gigachad.{left}"

        if right in ARROW_KEYS:
            prefix += " && config.gigachad.arrows"
            
        when_str = f"{prefix} && {when_str}" if when_str else prefix
        key_combo = f"{left}+{right}" if left else right
        key_combo = key_combo.replace('++', '+')  # Clean up accidental double plus
        visible_id = '_'.join(visible_combo) if visible_combo else 'none'
        gigachad_str = f"{key_combo}-gigachad-{dt_str}"
        command_str = f"{left.replace('+', '_')}.{right}.{when_focused}.{visible_id}.{gigachad_str}"
        keybindings.append({
            "_gigachad": gigachad_str,
            "key": key_combo,
            "command": command_str,
            "when": when_str
        })

print(json.dumps(keybindings, indent=4, ensure_ascii=False))
print(f"// Generated {len(keybindings)} keybindings")
