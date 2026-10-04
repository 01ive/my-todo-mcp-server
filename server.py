from fastmcp import FastMCP
import os
import re
import json
from datetime import datetime
from typing import Optional, List

mcp = FastMCP("TodoManager")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


TODO_FILE = os.path.join(PROJECT_ROOT, "tests", "toto.md")
STATUS_SYMBOLS = {"todo": "[ ]", "standby": "[/]", "done": "[x]"}
STATUS_ALIASES = {
    "todo": "todo",
    "non traitee": "todo",
    "non traitée": "todo",
    "standby": "standby",
    "standaby": "standby",
    "doing": "standby",
    "done": "done",
    "clos": "done",
    "closed": "done",
}
STATUS_BY_SYMBOL = {symbol: status for status, symbol in STATUS_SYMBOLS.items()}
TASK_LINE = re.compile(r"^(\s*-\s*)\[([ x/]?)\](\s*)(.*)$")
METADATA_PATTERNS = {
    "tags": re.compile(r"(?<!\S)#[\w-]+", re.UNICODE),
    "owner": re.compile(r"(?<!\S)@\S+"),
    "duration": re.compile(r"(?<!\S)~\S+"),
    "deadline": re.compile(r"(?<!\S)\d{4}-\d{2}-\d{2}(?!\S)"),
    "time_spent": re.compile(r"\$\d+(?:\.\d+)?(?:[A-Za-z%]+)"),
}

def read_lines():
    if not os.path.exists(TODO_FILE): return []
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        return f.readlines()

def save_lines(lines):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def normalize_status(status: str) -> Optional[str]:
    return STATUS_ALIASES.get(status.strip().lower())


def parse_task_line(line: str, section: str) -> Optional[dict]:
    match = TASK_LINE.match(line)
    if not match:
        return None

    symbol, content = match.group(2), match.group(4)
    metadata = {
        "tags": [],
        "owner": None,
        "duration": None,
        "deadline": None,
        "time_spent": None,
    }
    remaining_tokens = []

    for token in content.split():
        if token.startswith("#") and re.fullmatch(r"#[\w-]+", token):
            metadata["tags"].append(token[1:])
        elif token.startswith("@") and token != "@":
            metadata["owner"] = token[1:]
        elif token.startswith("~") and token != "~":
            metadata["duration"] = token[1:]
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
            metadata["deadline"] = token
        elif token.startswith("$") and token != "$":
            metadata["time_spent"] = token[1:]
        else:
            remaining_tokens.append(token)

    description = " ".join(remaining_tokens)

    return {
        "task": re.sub(r"\s+", " ", description).strip(),
        "section": section,
        "status": STATUS_BY_SYMBOL.get(f"[{symbol}]", "todo"),
        **metadata,
    }

@mcp.tool()
def get_todos() -> str:
    """Lit l'intégralité de la todo list."""
    if not os.path.exists(TODO_FILE): return "Fichier introuvable."
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        return f.read()


@mcp.tool()
def list_todos(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    owner: Optional[str] = None,
) -> str:
    """Retourne les tâches et leurs métadonnées en JSON, avec filtres facultatifs."""
    lines = read_lines()
    current_section = ""
    tasks = []
    normalized_filter = normalize_status(status) if status else None
    if status and normalized_filter is None:
        return "Statut invalide. Utilisez 'todo', 'standby' ou 'done'."

    for line in lines:
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            current_section = heading.group(1)
            continue
        task = parse_task_line(line, current_section)
        if task is None:
            continue
        if normalized_filter and task["status"] != normalized_filter:
            continue
        if tag and tag.lstrip("#").lower() not in [item.lower() for item in task["tags"]]:
            continue
        if owner and (task["owner"] or "").lower() != owner.lstrip("@").lower():
            continue
        tasks.append(task)

    return json.dumps(tasks, ensure_ascii=False, indent=2)

@mcp.tool()
def add_todo(
    task: str, 
    section: str = "Backlog",
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None,
    duration: Optional[str] = None,
    deadline: Optional[str] = None,
    time_spent: Optional[str] = None,
    status: str = "todo",
) -> str:
    """
    Ajoute une tâche formatée dans une rubrique.
    
    Args:
        task: Description de la tâche
        section: Nom de la rubrique (sans les ###)
        tags: Liste de tags (ex: ['design', 'dev'])
        owner: Responsable (ex: 'me', 'Olive')
        duration: Durée (ex: '1d', '3h', '1m')
        deadline: Date au format YYYY-MM-DD
        time_spent: Temps passé (ex: '$1h', '$30m') ou pourcentage de temp passé (ex: '$50%')
        status: 'todo' (non traitée), 'standby' (en attente) ou 'done' (clos)
    """
    normalized_status = normalize_status(status)
    if normalized_status is None:
        return "Statut invalide. Utilisez 'todo', 'standby' ou 'done'."
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            return "Date invalide. Utilisez le format YYYY-MM-DD."

    parts = [f"- {STATUS_SYMBOLS[normalized_status]} {task}"]
    
    if tags:
        parts.append(" ".join([f"#{t}" for t in tags]))
    if owner:
        parts.append(f"@{owner}")
    if duration:
        d = duration if duration.startswith("~") else f"~{duration}"
        parts.append(d)
    if deadline:
        parts.append(deadline)
    if time_spent:
        ts = time_spent if time_spent.startswith("$") else f"${time_spent}"
        parts.append(ts)

    new_line = " ".join(parts) + "\n"
    
    lines = read_lines()
    found = False
    for i, line in enumerate(lines):
        if f"###" in line and section.lower() in line.lower():
            lines.insert(i + 1, new_line)
            found = True
            break
            
    if not found:
        lines.append(f"\n### {section}\n")
        lines.append(new_line)
        
    save_lines(lines)
    return f"Tâche ajoutée avec succès dans {section}."


@mcp.tool()
def update_task_metadata(
    task_keyword: str,
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None,
    duration: Optional[str] = None,
    deadline: Optional[str] = None,
    time_spent: Optional[str] = None,
    clear_fields: Optional[List[str]] = None,
) -> str:
    """Met à jour les métadonnées fournies; clear_fields permet de les supprimer."""
    valid_fields = set(METADATA_PATTERNS)
    fields_to_clear = set(clear_fields or [])
    if fields_to_clear - valid_fields:
        return "Champ à effacer invalide. Utilisez tags, owner, duration, deadline ou time_spent."
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            return "Date invalide. Utilisez le format YYYY-MM-DD."

    updates = {
        "tags": tags,
        "owner": owner,
        "duration": duration,
        "deadline": deadline,
        "time_spent": time_spent,
    }
    for name, value in updates.items():
        if value is not None:
            fields_to_clear.add(name)

    lines = read_lines()
    for index, line in enumerate(lines):
        match = TASK_LINE.match(line)
        if not match or task_keyword.lower() not in match.group(4).lower():
            continue

        content = match.group(4)
        for name in fields_to_clear:
            content = METADATA_PATTERNS[name].sub("", content)
        additions = []
        for name, value in updates.items():
            if value is None:
                continue
            if name == "tags":
                additions.extend(f"#{tag.lstrip('#')}" for tag in value if tag.strip())
            elif value:
                prefix = {"owner": "@", "duration": "~", "time_spent": "$"}.get(name, "")
                additions.append(f"{prefix}{value.lstrip(prefix)}" if prefix else value)
        content = " ".join([content.strip(), *additions]).strip()
        lines[index] = f"{match.group(1)}[{match.group(2)}]{match.group(3)}{content}\n"
        save_lines(lines)
        return f"Métadonnées mises à jour pour : {task_keyword}"

    return "Tâche non trouvée."

@mcp.tool()
def update_task_status(task_keyword: str, status: str) -> str:
    """
    Change le statut : 'todo' (non traitée), 'standby' (en attente), 'done' (clos).
    """
    normalized_status = normalize_status(status)
    if normalized_status is None:
        return "Statut invalide. Utilisez 'todo', 'standby' ou 'done'."

    lines = read_lines()
    for i, line in enumerate(lines):
        if task_keyword.lower() in line.lower() and "- [" in line:
            lines[i] = re.sub(r"\[[ x/]?\]", STATUS_SYMBOLS[normalized_status], line, count=1)
            save_lines(lines)
            return f"Statut mis à jour pour : {task_keyword}"
            
    return "Tâche non trouvée."

if __name__ == "__main__":
    mcp.run()