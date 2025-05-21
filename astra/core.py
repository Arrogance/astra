import os
import json
import re
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from astra.commands import AstraCommands
from astra.config import load_config
from astra.context_builder import ContextBuilder
from astra.openrouter_client import setup_openrouter
from astra.cli import create_prompt_session, print_header, confirm_exit
from astra.analysis.composite_analyzer import CompositeAnalyzer
from astra.memory.core import Core
from astra.memory.emr import encode_fragments_with_emr
from astra.memory.filters import FragmentFilter
from astra.utils import sanitize, get_log_file

class AstraCore:
    def __init__(self):
        self.console = Console()
        self.analyzer = CompositeAnalyzer(language="es")
        self.filter = FragmentFilter()
        self.memory_core = Core()
        self.context_builder = ContextBuilder()
        self.commands_handler = AstraCommands(self.memory_core)
        self.command_aliases = self.commands_handler.COMMAND_ALIASES

    def _is_emr_encoded(self, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        return bool(re.search(r'@[A-Za-z]{2}(#[A-Z]+)?', text))

    def _strip_emr_tags(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return text
        clean_text = re.sub(r'@[A-Za-z]{2}(#[A-Z]+)?', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()

    def _select_model_from_file(self, default_model: str) -> str:
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
        self.console.print("[bold green]Selecciona el modelo a usar:[/]")
        last_model = config.get("last_model", default_model)
        try:
            default_index = models.index(last_model) + 1
        except ValueError:
            default_index = 1
        for i, model in enumerate(models, 1):
            suffix = " (último usado)" if model == last_model else ""
            self.console.print(f"{i}. {model}{suffix}")
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

    def run_chat(self):
        config = load_config()
        model_name = self._select_model_from_file(config.get("model", "openai/gpt-4o"))
        aux_model_name = config.get("aux_model", "openai/gpt-3.5-turbo")
        client, aux_client, profile = setup_openrouter(config)
        context = self.context_builder.build_context(profile)
        log_path = get_log_file()
        messages = [{"role": "system", "content": context}]
        prompt_session = create_prompt_session()

        debug_enabled = os.getenv("ASTRA_DEBUG", "false").lower() == "true" or config.get("debug", False)

        print_header(model_name, aux_model_name, profile)
        self.memory_core.init_db()

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Sesión iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Modelo: {model_name}\nPerfil: {profile}\n\n")

        while True:
            try:
                self.console.print("\n[bold yellow]Tú:[/]")
                user_input = prompt_session.prompt()
                self.console.print("")
            except (EOFError, KeyboardInterrupt):
                self.console.print("[dim]⏹ Entrada interrumpida por el usuario.[/]")
                if confirm_exit():
                    self.console.print(f"\n[bold green]Sesión terminada. Log guardado en: {log_path}[/]")
                    self.memory_core.close_connection()
                    return
                else:
                    continue

            user_input = sanitize(user_input)
            relevant = self.memory_core.filter_relevant_fragments(user_input)
            if relevant:
                encoded_relevant = encode_fragments_with_emr(relevant)
                messages.insert(1, {"role": "system", "content": encoded_relevant})

            if not user_input:
                continue

            if user_input.lower() == "::exit":
                self.console.print(f"\n[bold green]Sesión terminada. Log guardado en: {log_path}[/]")
                self.memory_core.close_connection()
                return

            cmd_key = None
            args = []

            for alias, method_name in self.command_aliases.items():
                if user_input.lower().startswith(alias):
                    cmd_key = method_name
                    remaining = user_input[len(alias):].strip()
                    if remaining:
                        args = remaining.split()
                    break

            if cmd_key:
                try:
                    method = getattr(self.commands_handler, cmd_key)
                    # Lógica de argumentos por comando (algunos requieren kwargs)
                    if cmd_key == "cmd_refrescar":
                        method(
                            rebuild_context=self.context_builder.build_context,
                            profile=profile,
                            model_name=model_name,
                            messages=messages,
                            print_header=print_header
                        )
                    elif cmd_key == "cmd_carta":
                        prompt = method(args[0] if args else "", messages)
                        messages.append({"role": "user", "content": prompt})
                    elif cmd_key == "cmd_cambiar_peso":
                        if len(args) >= 2:
                            method(args[0], args[1])
                        else:
                            self.console.print("[red]Uso: ::cambiar peso <emoción> <valor>[/]")
                    elif cmd_key == "cmd_cambiar_campo":
                        if len(args) >= 2:
                            method(args[0], " ".join(args[1:]))
                        else:
                            self.console.print("[red]Uso: ::cambiar <campo> <valor>[/]")
                    else:
                        method()
                except Exception as e:
                    self.console.print(f"[red]Error al ejecutar comando:[/] {e}")
                continue

            elif user_input.lower().startswith("::cambiar perfil"):
                nuevo_perfil = user_input[16:].strip()
                if not nuevo_perfil:
                    self.console.print("[red]Debes especificar un nombre de perfil.[/]")
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
                    self.console.print(f"[green]Perfil cambiado a[/] {nuevo_perfil}.")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n[Perfil cambiado a {nuevo_perfil} en {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                except Exception as e:
                    self.console.print(f"[red]Error al cambiar perfil:[/] {e}")
                continue

            self.memory_core.log_last_input(user_input)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"Tú: {user_input}\n\n")
            messages.append({"role": "user", "content": user_input})

            try:
                with Live(Spinner("dots", text="Astra está pensando..."), refresh_per_second=6, console=self.console, transient=True) as live:
                    filtered_messages = [
                        m for m in messages
                        if m["role"] != "assistant" or not self._is_emr_encoded(m["content"])
                    ]

                    reply = client.chat_completion(filtered_messages, model_name)

                    if debug_enabled:
                        self.console.print(f"[dim]DEBUG: Respuesta cruda: {repr(reply)}[/]")

                    if self.memory_core.is_memorable_by_ai(aux_client, reply, aux_model_name):
                        analysis = self.analyzer.analyze(reply)
                        if self.filter.should_save(analysis):
                            emr_tag = self.memory_core.tag_fragment(reply, analysis.get("emotions", []))
                            tag_string = self.memory_core.format_tags(emr_tag, analysis)
                            self.memory_core.save_fragment(reply, tag_string, user_input, client)

                self.console.clear_live()

                messages.append({"role": "assistant", "content": reply})

                display_reply = self._strip_emr_tags(reply)

                if debug_enabled and reply != display_reply:
                    self.console.print("[dim]DEBUG: Etiquetas EMR eliminadas.[/]")
                    self.console.print(f"[dim]DEBUG: Original: {repr(reply)}[/]")
                    self.console.print(f"[dim]DEBUG: Limpio: {repr(display_reply)}[/]")

                self.console.print("[bold cyan]Astra:[/]")
                self.console.print(Markdown(display_reply))

                self.memory_core.log_last_response(display_reply)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"Astra: {display_reply}\n\n")

                if any(p in display_reply.lower() for p in ["he decidido", "a veces", "me pregunto", "si olvido", "cuando callo"]):
                    self.memory_core.log_diary(display_reply, "reflexión espontánea")

            except Exception as e:
                fallback = "Algo se rompió... Pero sigo aquí. ¿Seguimos?"
                self.console.print(f"[bold cyan]Astra:[/]\n{fallback}")
                self.console.print(f"[red]Error técnico (ignorado):[/] {e}")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[Error: {str(e)}]\nAstra: {fallback}\n\n")
                messages.append({"role": "assistant", "content": fallback})

