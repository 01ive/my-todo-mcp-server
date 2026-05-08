from fastmcp import FastMCP
import os
import re
from datetime import datetime
from typing import Optional, List

mcp = FastMCP("TodoManager")

TODO_FILE = r"C:\DATA\workspace\todo\exemple.md"

def read_lines():
    if not os.path.exists(TODO_FILE): return []
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        return f.readlines()

def save_lines(lines):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

@mcp.tool()
def get_todos() -> str:
    """Lit l'intégralité de la todo list."""
    if not os.path.exists(TODO_FILE): return "Fichier introuvable."
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
def add_todo(
    task: str, 
    section: str = "Backlog",
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None,
    duration: Optional[str] = None,
    deadline: Optional[str] = None
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
    """
    # Construction de la ligne selon ton formalisme
    parts = [f"- [ ] {task}"]
    
    if tags:
        parts.append(" ".join([f"#{t}" for t in tags]))
    if owner:
        parts.append(f"@{owner}")
    if duration:
        # On vérifie si le ~ est déjà là, sinon on l'ajoute
        d = duration if duration.startswith("~") else f"~{duration}"
        parts.append(d)
    if deadline:
        parts.append(deadline)

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
def update_task_status(task_keyword: str, status: str) -> str:
    """
    Change le statut d'une tâche : 'todo' ([ ]), 'doing' ([/]), 'done' ([x]).
    """
    status_symbols = {"todo": "[ ]", "doing": "[/]", "done": "[x]"}
    if status not in status_symbols:
        return "Statut invalide. Utilisez 'todo', 'doing' ou 'done'."

    lines = read_lines()
    for i, line in enumerate(lines):
        if task_keyword.lower() in line.lower() and "- [" in line:
            # Regex pour remplacer le contenu entre crochets sans toucher au reste
            lines[i] = re.sub(r"\[[ x/]?\]", status_symbols[status], line)
            save_lines(lines)
            return f"Statut mis à jour pour : {task_keyword}"
            
    return "Tâche non trouvée."

if __name__ == "__main__":
    mcp.run()