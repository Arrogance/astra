# === as astra/core.py ===

import os
import json
import re
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

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

import importlib
import inspect
from astra import commands

def load_commands():
    return {
        name: func for name, func in inspect.getmembers(commands, inspect.isfunction)
        if name.startswith("cmd_")
    }

COMMANDS = load_commands()
COMMAND_ALIASES = getattr(commands, "COMMAND_ALIASES", {})

console = Console()

def is_emr_encoded(text: str) -> bool:
    text = text.strip()
    return bool(re.match(r"^@([A-Z]{2})(#[A-Z]+)?\s", text))

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

    config["last_aux_model"] = selected_model
    config["aux_model"] = selected_model

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

    print_header(model_name, profile)
    init_db()

    while True:
        try:
            console.print("[bold yellow]Tú:[/]")
            user_input = prompt_session.prompt()
            console.print("")
        except (EOFError, KeyboardInterrupt):
            console.print("[dim]⏹ Entrada interrumpida por el usuario.[/]")
            if confirm_exit():
                close_connection()
                return
            else:
                continue

        user_input = sanitize(user_input)
        relevant = filter_relevant_fragments(user_input)
        if relevant:
            messages.insert(1, {"role": "system", "content": "\n".join(relevant)})

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
            except Exception as e:
                console.print(f"[red]Error al cambiar perfil:[/] {e}")
            continue

        log_last_input(user_input)
        messages.append({"role": "user", "content": user_input})

        try:
            with Live(Spinner("dots", text="Astra está pensando..."), refresh_per_second=6, console=console) as live:
                filtered_messages = [
                    m for m in messages
                    if m["role"] != "assistant" or not is_emr_encoded(m["content"])
                ]

                reply = client.chat_completion(filtered_messages, model_name)

                # Ahora verificamos si es memorable con el aux_client
                if is_memorable_by_ai(client, reply, aux_client, aux_model_name):
                    tag = tag_fragment(reply)
                    save_fragment(reply, tag, user_input, client)

            # fuera del `with`, una vez el spinner termina
            if is_emr_encoded(reply):
                continue

            messages.append({"role": "assistant", "content": reply})
            console.print(f"\n[bold cyan]Astra:[/]\n{reply}")
            log_last_response(reply)

            if any(p in reply.lower() for p in ["he decidido", "a veces", "me pregunto", "si olvido", "cuando callo"]):
                log_diary(reply, "reflexión espontánea")

        except Exception as e:
            fallback = "Algo se rompió... Pero sigo aquí. ¿Seguimos?"
            console.print(f"\n[bold cyan]Astra:[/]\n{fallback}\n")
            console.print(f"[red]Error técnico (ignorado):[/] {e}")
            messages.append({"role": "assistant", "content": fallback})
