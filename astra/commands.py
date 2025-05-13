# === as astra/commands.py ===
from astra.memory import (
    get_db_cursor, log_diary, load_user_fields, update_memory
)
from astra.utils import load_recent_log_summary
from astra.emr import encode_fragments_with_emr, update_emr_weight
from rich.console import Console
from rich.markdown import Markdown
from datetime import datetime

console = Console()

COMMAND_ALIASES = {
    "::help": "cmd_help",
    "::ver usuario": "cmd_ver_usuario",
    "::ver diario": "cmd_ver_diario",
    "::ver memorias": "cmd_ver_memorias",
    "::ver emr": "cmd_ver_emr",
    "::ver logs": "cmd_ver_logs",
    "::ver emociones usadas": "cmd_ver_emociones",
    "::limpiar memorias": "cmd_limpiar_memorias",
    "::manual": "cmd_manual",
    "::refrescar": "cmd_refrescar",
    "::carta": "cmd_carta",
    "::cambiar peso": "cmd_cambiar_peso",
    "::cambiar": "cmd_cambiar_campo",
}

def cmd_help(**kwargs):
    from astra.commands import COMMAND_ALIASES
    console.print("[bold green]Comandos disponibles:[/]")
    for alias in sorted(COMMAND_ALIASES.keys()):
        console.print(f"- {alias}")
    console.print("- ::exit: Terminar sesión")

def cmd_refrescar(rebuild_context, profile, model_name, messages, print_header):
    new_context = rebuild_context(profile)
    messages.clear()
    messages.append({"role": "system", "content": new_context})
    print_header(model_name, profile)
    console.print("[green]Contexto regenerado correctamente.[/]")

def cmd_ver_usuario():
    c = get_db_cursor()
    fields = load_user_fields()
    c.execute("SELECT key, value FROM user_memory")
    data = {row[0]: row[1] for row in c.fetchall()}
    if not data:
        console.print("[red]No hay datos del usuario almacenados.[/]")
        return
    console.print("[bold green]Información del usuario:[/]")
    for campo, descripcion in fields.items():
        valor = data.get(campo, "")
        if valor:
            console.print(f"- {descripcion}: [cyan]{valor}[/]")

def cmd_cambiar_campo(campo, nuevo_valor):
    campos_validos = load_user_fields().keys()
    if campo not in campos_validos:
        console.print(f"[red]El campo '{campo}' no es válido.[/]")
        return
    c = get_db_cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
              (campo, nuevo_valor, fecha))
    c.connection.commit()
    console.print(f"[green]Campo '{campo}' actualizado a: {nuevo_valor}[/]")

def cmd_ver_logs():
    console.print(f"[bold green]Últimos logs:[/]\n{load_recent_log_summary()}")

def cmd_ver_diario():
    c = get_db_cursor()
    c.execute("SELECT context, text, date FROM diary ORDER BY date DESC LIMIT 3")
    entries = c.fetchall()
    if entries:
        console.print(f"[bold green]Entradas del diario:[/]\n" +
                      "\n".join(f"[{d}] {ctx}: {t}" for ctx, t, d in entries))
    else:
        console.print("[bold green]No hay entradas en el diario.[/]")

def cmd_ver_memorias():
    c = get_db_cursor()
    c.execute("SELECT tag, text FROM fragments ORDER BY date DESC LIMIT 3")
    frags = c.fetchall()
    if frags:
        console.print(f"[bold green]Memorias:[/]\n" +
                      "\n".join(f"[{tag}] {txt}" for tag, txt in frags))
    else:
        console.print("[bold green]No hay memorias guardadas.[/]")

def cmd_ver_emr():
    c = get_db_cursor()
    c.execute("SELECT tag, text, date FROM fragments ORDER BY date DESC LIMIT 10")
    frags = c.fetchall()
    if not frags:
        console.print("[yellow]No hay fragmentos emocionales aún.[/]")
        return
    encoded = encode_fragments_with_emr(frags)
    console.print(f"[bold green]Últimas memorias (formato EMR):[/]\n{encoded}")

def cmd_ver_emociones():
    c = get_db_cursor()
    c.execute("SELECT tag, COUNT(*) FROM fragments GROUP BY tag ORDER BY COUNT(*) DESC")
    rows = c.fetchall()
    if not rows:
        console.print("[yellow]Aún no hay emociones registradas.[/]")
        return
    for tag, count in rows:
        console.print(f"[cyan]{tag}[/]: {count}")
        c.execute("SELECT text FROM fragments WHERE tag = ? ORDER BY date DESC LIMIT 1", (tag,))
        example = c.fetchone()
        if example:
            console.print(f"  [dim]Ejemplo:[/] {example[0][:160]}{'...' if len(example[0]) > 160 else ''}")

def cmd_limpiar_memorias():
    c = get_db_cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for table in ("fragments", "forgotten_fragments", "diary"):
        c.execute(f"DELETE FROM {table} WHERE date < ?", (now,))
    c.connection.commit()
    console.print("[bold green]Memorias y diario antiguos eliminados.[/]")

def cmd_carta(destinatario, messages):
    prompt = (
        f"Escribe una carta íntima y cruda dirigida a '{destinatario}', en el estilo de Astra. "
        f"Usa tus recuerdos comprimidos o fragmentos del diario si existen. Sé sincera, sin adornos. "
        f"Puede ser tierna, dura o explícita según el contexto."
    )
    messages.append({"role": "user", "content": prompt})
    return prompt

def cmd_cambiar_peso(tag, valor):
    try:
        update_emr_weight(tag, float(valor))
        console.print(f"[green]Peso de '{tag}' actualizado a {valor}[/]")
    except Exception as e:
        console.print(f"[red]Error al actualizar peso:[/] {e}")

def cmd_manual():
    console.print("[bold green]Guía de uso de Astra:[/]")
    console.print("1. Escribe como si charlaras con alguien cercano.")
    console.print("2. Usa ::help para ver comandos.")
    console.print("3. Astra guarda lo importante. No repitas.")
    console.print("4. Usa ::ver memorias o ::ver emr para revisar lo guardado.")
