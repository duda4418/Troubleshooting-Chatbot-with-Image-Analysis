from typing import List, Dict

def actions_to_text(actions: List[Dict]) -> str:
    lines = []
    for a in actions:
        lines.append(f"• {a['type'].capitalize()} → {a['target'].replace('_',' ')}: **{a['value']}**")
    return "\n".join(lines)
