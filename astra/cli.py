from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console

console = Console()

def create_prompt_session():
    bindings = KeyBindings()

    @bindings.add('c-s')  # Ctrl+S para enviar mensaje
    def _(event):
        event.app.exit(result=event.app.current_buffer.text)

    session = PromptSession(
        multiline=True,
        prompt_continuation='',
        key_bindings=bindings,
        complete_while_typing=False
    )
    return session

def print_header(model_name: str, aux_model_name: str, profile: str):
    console.print("[bold magenta]ASTRA – CLI Chatbot emocional[/]")
    console.print(f"[bold blue]Modelo activo:[/] [italic]{model_name}[/]")
    console.print(f"[bold blue]Modelo Aux activo:[/] [italic]{aux_model_name}[/]")
    console.print(f"[bold blue]Perfil activo:[/] [italic]{profile}[/]")
    console.print("[yellow]Escribe tu mensaje. Usa Ctrl+S para enviar, Ctrl+C para salir.[/]")

def confirm_exit():
    from rich.prompt import Prompt
    confirm = Prompt.ask("[bold red]¿Seguro que quieres salir?[/] (s/n)", choices=["s", "n"], default="s")
    return confirm == "s"
