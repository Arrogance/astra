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
    console.print("[bold magenta]ASTRA - Emotional CLI Chatbot[/]")
    console.print(f"[bold blue]Active model:[/] [italic]{model_name}[/]")
    console.print(f"[bold blue]Active Aux model:[/] [italic]{aux_model_name}[/]")
    console.print(f"[bold blue]Active profile:[/] [italic]{profile}[/]")
    console.print("[yellow]Type your message. Use Ctrl+S to send, Ctrl+C to exit.[/]")
    
    def confirm_exit():
    from rich.prompt import Prompt
    confirm = Prompt.ask("[bold red]Are you sure you want to exit?[/] (y/n)", choices=["y", "n"], default="y")
    return confirm == "s"
