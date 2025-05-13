# === as astra/core.py ===

import os
import json
import re
import importlib
import inspect
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from astra import commands
from astra.config import load_config
from astra.context_builder import build_context
from astra.openrouter_client import setup_openrouter
from astra.cli import create_prompt_session, print_header, confirm_exit
from astra.memory import (
    init_db, close_connection, log_last_input, log_last_response,
    save_fragment, extract_memory_note, update_memory, log_diary,
    filter_relevant_fragments, is_memorable_by_ai, tag_fragment
)
from astra.utils import sanitize, tone_needs_grounding, get_log_file
from astra.emr import encode_fragments_with_emr

def load_commands():
    return {
        name: func for name, func in inspect.getmembers(commands, inspect.isfunction)
        if name.startswith("cmd_")
    }

COMMANDS = load_commands()
COMMAND_ALIASES = getattr(commands, "COMMAND_ALIASES", {})

console = Console()

def is_emr_encoded(text: str) -> bool:
    """
    Verifica si el texto contiene alguna etiqueta EMR (como @RB#NOW).
    """
    if not text or not isinstance(text, str):
        return False
    # Busca cualquier patrón @XX o @XX#YYY
    return bool(re.search(r'@[A-Za-z]{2}(#[A-Z]+)?', text))

def strip_emr_tags(text: str) -> str:
    """
    Elimina agresivamente todas las etiquetas EMR (como @RB#NOW @ID#NOW) de una respuesta,
    sin importar dónde aparezcan o cómo estén formateadas.
    """
    if not text or not isinstance(text, str):
        return text

    # Busca y elimina todas las etiquetas EMR en cualquier parte del texto
    # Patrón más agresivo que captura @XX seguido opcionalmente de #YYY
    clean_text = re.sub(r'@[A-Za-z]{2}(#[A-Z]+)?', '', text)

    # Elimina espacios duplicados que podrían quedar
    clean_text = re.sub(r'\s+', ' ', clean_text)

    return clean_text.strip()

def select_model_from_file(default_model: str) -> str:
    path = "models.txt"
    config_path = "config.json"
    if not os.path.exists(path):
        return default_model
    with open(path, "r", encoding="utf-8") as f:
        models = [line.strip() for line in f if line.strip()]
    if not models:
        return default_model
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        config = {}

    console.print("[bold green]Selecciona el modelo a usar:[/]")
    last_model = config.get("last_model", default_model)

    try:
        default_index = models.index(last_model) + 1
    except ValueError:
        default_index = 1

    for i, model in enumerate(models, 1):
        suffix = " (último usado)" if model == last_model else ""
        console.print(f"{i}. {model}{suffix}")
    choice = Prompt.ask("[bold yellow]Número del modelo[/]", default=str(default_index))
    try:
        index = int(choice) - 1
        selected_model = models[index]
    except Exception:
        selected_model = models[default_index - 1]

    config["last_model"] = selected_model
    config["model"] = selected_model

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return selected_model

def chat():
    config = load_config()
    model_name = select_model_from_file(config.get("model", "openai/gpt-4o"))
    aux_model_name = config.get("aux_model", "openai/gpt-3.5-turbo")
    client, aux_client, profile = setup_openrouter(config)
    context = build_context(profile)
    log_path = get_log_file()
    messages = [{"role": "system", "content": context}]
    prompt_session = create_prompt_session()

    # Verificar si la depuración está habilitada
    debug_enabled = os.getenv("ASTRA_DEBUG", "false").lower() == "true" or config.get("debug", False)

    print_header(model_name, aux_model_name, profile)
    init_db()

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Sesión iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Modelo: {model_name}\nPerfil: {profile}\n\n")

    while True:
        try:
            console.print("\n[bold yellow]Tú:[/]")
            user_input = prompt_session.prompt()
            console.print("")
        except (EOFError, KeyboardInterrupt):
            console.print("[dim]⏹ Entrada interrumpida por el usuario.[/]")
            if confirm_exit():
                console.print(f"\n[bold green]Sesión terminada. Log guardado en: {log_path}[/]")
                close_connection()
                return
            else:
                continue

        user_input = sanitize(user_input)
        relevant = filter_relevant_fragments(user_input)
        if relevant:
            encoded_relevant = encode_fragments_with_emr(relevant)
            messages.insert(1, {"role": "system", "content": encoded_relevant})

        if not user_input:
            continue

        if user_input.lower() == "::exit":
            console.print(f"\n[bold green]Sesión terminada. Log guardado en: {log_path}[/]")
            close_connection()
            return

        cmd_key = None
        args = []

        for alias, command in COMMAND_ALIASES.items():
            if user_input.lower().startswith(alias):
                cmd_key = command
                remaining = user_input[len(alias):].strip()
                if remaining:
                    args = remaining.split()
                break

        if cmd_key:
            try:
                if cmd_key == "cmd_refrescar":
                    COMMANDS[cmd_key](
                        rebuild_context=build_context,
                        profile=profile,
                        model_name=model_name,
                        messages=messages,
                        print_header=print_header
                    )
                elif cmd_key == "cmd_carta":
                    prompt = COMMANDS[cmd_key](args[0], messages)
                    messages.append({"role": "user", "content": prompt})
                elif cmd_key == "cmd_cambiar_peso":
                    if len(args) >= 2:
                        COMMANDS[cmd_key](args[0], args[1])
                    else:
                        console.print("[red]Uso: ::cambiar peso <emoción> <valor>[/]")
                elif cmd_key == "cmd_cambiar_campo":
                    if len(args) >= 2:
                        COMMANDS[cmd_key](args[0], " ".join(args[1:]))
                    else:
                        console.print("[red]Uso: ::cambiar <campo> <valor>[/]")
                else:
                    COMMANDS[cmd_key]()
            except Exception as e:
                console.print(f"[red]Error al ejecutar comando:[/] {e}")
            continue

        elif user_input.lower().startswith("::cambiar perfil"):
            nuevo_perfil = user_input[16:].strip()
            if not nuevo_perfil:
                console.print("[red]Debes especificar un nombre de perfil.[/]")
                continue
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["profile"] = nuevo_perfil
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                profile = nuevo_perfil
                context = build_context(profile)
                messages = [{"role": "system", "content": context}]
                console.print(f"[green]Perfil cambiado a[/] {nuevo_perfil}.")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[Perfil cambiado a {nuevo_perfil} en {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
            except Exception as e:
                console.print(f"[red]Error al cambiar perfil:[/] {e}")
            continue

        log_last_input(user_input)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"Tú: {user_input}\n\n")
        messages.append({"role": "user", "content": user_input})

        try:
            with Live(Spinner("dots", text="Astra está pensando..."), refresh_per_second=6, console=console, transient=True) as live:
                filtered_messages = [
                    m for m in messages
                    if m["role"] != "assistant" or not is_emr_encoded(m["content"])
                ]

                reply = client.chat_completion(filtered_messages, model_name)

                # Depuración condicional
                if debug_enabled:
                    console.print(f"[dim]DEBUG: Respuesta cruda: {repr(reply)}[/]")

                # Verificamos si es memorable con el aux_client
                if is_memorable_by_ai(client, reply, aux_client, aux_model_name):
                    tag = tag_fragment(reply)
                    save_fragment(reply, tag, user_input, client)

            console.clear_live()

            # Guardar la respuesta original con EMR en mensajes para el modelo
            messages.append({"role": "assistant", "content": reply})

            # Limpieza agresiva de etiquetas EMR para mostrar al usuario
            display_reply = strip_emr_tags(reply)

            # Depuración si está habilitada
            if debug_enabled and reply != display_reply:
                console.print(f"[dim]DEBUG: Etiquetas EMR eliminadas.[/]")
                console.print(f"[dim]DEBUG: Original: {repr(reply)}[/]")
                console.print(f"[dim]DEBUG: Limpio: {repr(display_reply)}[/]")

            # Procesar la respuesta como markdown y mostrarla
            console.print(f"[bold cyan]Astra:[/]")  # Imprimir el prefijo
            console.print(Markdown(display_reply))  # Renderizar la respuesta como markdown

            # Registrar la versión limpia en el historial y log
            log_last_response(display_reply)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"Astra: {display_reply}\n\n")

            # Verificar si contiene patrones para el diario
            if any(p in display_reply.lower() for p in ["he decidido", "a veces", "me pregunto", "si olvido", "cuando callo"]):
                log_diary(display_reply, "reflexión espontánea")

        except Exception as e:
            fallback = "Algo se rompió... Pero sigo aquí. ¿Seguimos?"
            console.print(f"[bold cyan]Astra:[/]\n{fallback}")
            console.print(f"[red]Error técnico (ignorado):[/] {e}")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[Error: {str(e)}]\nAstra: {fallback}\n\n")
            messages.append({"role": "assistant", "content": fallback})
