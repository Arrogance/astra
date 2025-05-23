from astra.memory.core import Core
from astra.utils import load_recent_log_summary
from astra.memory.emr import encode_fragments_with_emr, update_emr_weight
from rich.console import Console
from datetime import datetime

class AstraCommands:
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

    def __init__(self, core: Core = None):
        self.core = core if core else Core()
        self.console = Console()

    def cmd_help(self, **kwargs):
        self.console.print("[bold green]Comandos disponibles:[/]")
        for alias in sorted(self.COMMAND_ALIASES.keys()):
            self.console.print(f"- {alias}")
        self.console.print("- ::exit: Terminar sesión")

    def cmd_refrescar(self, rebuild_context, profile, model_name, messages, print_header):
        new_context = rebuild_context(profile)
        messages.clear()
        messages.append({"role": "system", "content": new_context})
        print_header(model_name, profile)
        self.console.print("[green]Contexto regenerado correctamente.[/]")

    def cmd_ver_usuario(self):
        c = self.core.get_db_cursor()
        fields = self.core.load_user_fields()
        c.execute("SELECT key, value FROM user_memory")
        data = {row[0]: row[1] for row in c.fetchall()}
        if not data:
            self.console.print("[red]No hay datos del usuario almacenados.[/]")
            return
        self.console.print("[bold green]Información del usuario:[/]")
        for campo, descripcion in fields.items():
            valor = data.get(campo, "")
            if valor:
                self.console.print(f"- {descripcion}: [cyan]{valor}[/]")

    def cmd_cambiar_campo(self, campo, nuevo_valor):
        campos_validos = self.core.load_user_fields().keys()
        if campo not in campos_validos:
            self.console.print(f"[red]El campo '{campo}' no es válido.[/]")
            return
        c = self.core.get_db_cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO user_memory (key, value, date) VALUES (?, ?, ?)",
                  (campo, nuevo_valor, fecha))
        c.connection.commit()
        self.console.print(f"[green]Campo '{campo}' actualizado a: {nuevo_valor}[/]")

    def cmd_ver_logs(self):
        self.console.print(f"[bold green]Últimos logs:[/]\n{load_recent_log_summary()}")

    def cmd_ver_diario(self):
        c = self.core.get_db_cursor()
        c.execute("SELECT context, text, date FROM diary ORDER BY date DESC LIMIT 3")
        entries = c.fetchall()
        if entries:
            self.console.print("[bold green]Entradas del diario:[/]\n" +
                          "\n".join(f"[{d}] {ctx}: {t}" for ctx, t, d in entries))
        else:
            self.console.print("[bold green]No hay entradas en el diario.[/]")

    def cmd_ver_memorias(self):
        c = self.core.get_db_cursor()
        c.execute("SELECT tag, text FROM fragments ORDER BY date DESC LIMIT 3")
        frags = c.fetchall()
        if frags:
            self.console.print("[bold green]Memorias:[/]\n" +
                          "\n".join(f"[{tag}] {txt}" for tag, txt in frags))
        else:
            self.console.print("[bold green]No hay memorias guardadas.[/]")

    def cmd_ver_emr(self):
        c = self.core.get_db_cursor()
        c.execute("SELECT tag, text, date FROM fragments ORDER BY date DESC LIMIT 10")
        frags = c.fetchall()
        if not frags:
            self.console.print("[yellow]No hay fragmentos emocionales aún.[/]")
            return
        encoded = encode_fragments_with_emr(frags)
        self.console.print(f"[bold green]Últimas memorias (formato EMR):[/]\n{encoded}")

    def cmd_ver_emociones(self):
        c = self.core.get_db_cursor()
        c.execute("SELECT tag, COUNT(*) FROM fragments GROUP BY tag ORDER BY COUNT(*) DESC")
        rows = c.fetchall()
        if not rows:
            self.console.print("[yellow]Aún no hay emociones registradas.[/]")
            return
        for tag, count in rows:
            self.console.print(f"[cyan]{tag}[/]: {count}")
            c.execute("SELECT text FROM fragments WHERE tag = ? ORDER BY date DESC LIMIT 1", (tag,))
            example = c.fetchone()
            if example:
                self.console.print(f"  [dim]Ejemplo:[/] {example[0][:160]}{'...' if len(example[0]) > 160 else ''}")

    def cmd_limpiar_memorias(self):
        c = self.core.get_db_cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for table in ("fragments", "forgotten_fragments", "diary"):
            c.execute(f"DELETE FROM {table} WHERE date < ?", (now,))
        c.connection.commit()
        self.console.print("[bold green]Memorias y diario antiguos eliminados.[/]")

    def cmd_carta(self, destinatario, messages):
        prompt = (
            f"Escribe una carta íntima y cruda dirigida a '{destinatario}', en el estilo de Astra. "
            f"Usa tus recuerdos comprimidos o fragmentos del diario si existen. Sé sincera, sin adornos. "
            f"Puede ser tierna, dura o explícita según el contexto."
        )
        messages.append({"role": "user", "content": prompt})
        return prompt

    def cmd_cambiar_peso(self, tag, valor):
        try:
            update_emr_weight(tag, float(valor))
            self.console.print(f"[green]Peso de '{tag}' actualizado a {valor}[/]")
        except Exception as e:
            self.console.print(f"[red]Error al actualizar peso:[/] {e}")

    def cmd_manual(self):
        self.console.print("[bold green]Guía de uso de Astra:[/]")
        self.console.print("1. Escribe como si charlaras con alguien cercano.")
        self.console.print("2. Usa ::help para ver comandos.")
        self.console.print("3. Astra guarda lo importante. No repitas.")
        self.console.print("4. Usa ::ver memorias o ::ver emr para revisar lo guardado.")

# Atajo para acceso simple desde fuera:
COMMAND_ALIASES = AstraCommands.COMMAND_ALIASES
