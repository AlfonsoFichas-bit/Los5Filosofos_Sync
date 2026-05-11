import math
import threading
from collections import deque

from rich.console import Group
from rich.markup import escape as markup_escape
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, RichLog, Button, Label

from core import CFG, N, PENSANDO, HAMBRIENTO, COMIENDO, NOMBRES, EMOJIS, ESTADO_STR, Snapshot
from mesa import MesaFilosofos


class MesaVisual(Static):
    POSICIONES = [(0, 21), (4, 37), (13, 33), (13, 5), (4, 3)]
    TEN_POS = [(2, 31), (9, 37), (15, 21), (9, 5), (2, 13)]
    ANCHO = 49
    ALTURA = 19

    def __init__(self, mesa: MesaFilosofos, **kwargs):
        super().__init__(**kwargs)
        self.mesa = mesa

    def _tenedor_libre(self, snap: Snapshot, t: int) -> bool:
        return not (snap.estado[t] == COMIENDO or snap.estado[(t + 1) % N] == COMIENDO)

    def render(self):
        snap = self.mesa.snapshot()
        colores = {PENSANDO: "cyan", HAMBRIENTO: "yellow", COMIENDO: "green"}
        grid = [[" "] * self.ANCHO for _ in range(self.ALTURA)]

        cx, cy = 24, 9
        rx, ry = 22, 8.5
        for deg in range(0, 360, 2):
            rad = math.radians(deg)
            col = int(cx + rx * math.cos(rad))
            row = int(cy + ry * math.sin(rad) * 0.55)
            if 0 <= row < self.ALTURA and 0 <= col < self.ANCHO:
                grid[row][col] = "·"

        lines = []
        sep = "─" * (self.ANCHO + 2)

        header = Text()
        header.append("┌", style="bold white")
        header.append(sep, style="bold white")
        header.append("┐", style="bold white")
        lines.append(header)

        for r in range(self.ALTURA):
            row_text = Text()
            row_text.append("│ ", style="bold white")
            overrides = {}

            for i, (pr, pc) in enumerate(self.POSICIONES):
                if pr == r:
                    color = colores[snap.estado[i]]
                    ficha = f"{EMOJIS[i]}F{i}"
                    for k, ch in enumerate(ficha):
                        overrides[pc + k] = (ch, color)

            for t, (tr, tc) in enumerate(self.TEN_POS):
                if tr == r:
                    libre = self._tenedor_libre(snap, t)
                    sym = "🍴" if libre else "🥄"
                    style = "bold green" if libre else "bold red"
                    overrides[tc] = (sym, style)

            if r == 9:
                overrides[cx - 1] = ("🍝", "white")

            c = 0
            while c < self.ANCHO:
                if c in overrides:
                    ch, st = overrides[c]
                    row_text.append(ch, style=st)
                else:
                    base = grid[r][c]
                    row_text.append(base, style="dim white" if base == "·" else "")
                c += 1

            row_text.append(" │", style="bold white")
            lines.append(row_text)

        footer = Text()
        footer.append("└", style="bold white")
        footer.append(sep, style="bold white")
        footer.append("┘", style="bold white")
        lines.append(footer)

        leyenda = Text(" ")
        leyenda.append("🍴 Libre ", style="bold green")
        leyenda.append(" 🥄 Tomado", style="bold red")
        lines.append(leyenda)

        est_ley = Text(" ")
        est_ley.append("■ Pensando ", style="cyan")
        est_ley.append("■ Hambriento ", style="yellow")
        est_ley.append("■ Comiendo", style="green")
        lines.append(est_ley)

        return Group(*lines)


class TablaEstados(Static):
    def __init__(self, mesa: MesaFilosofos, **kwargs):
        super().__init__(**kwargs)
        self.mesa = mesa

    def render(self):
        snap = self.mesa.snapshot()
        table = Table(
            title="[bold white]⚡ Estado de los Filósofos[/bold white]",
            expand=True,
            border_style="bright_black",
            header_style="bold white",
            show_lines=True,
        )
        table.add_column("Filósofo",  style="bold white", no_wrap=True, min_width=22)
        table.add_column("Estado",    justify="center",   min_width=18)
        table.add_column("Ten. Izq",  justify="center",   min_width=11)
        table.add_column("Ten. Der",  justify="center",   min_width=11)
        table.add_column("🍝 Comidas", justify="center",  style="bold cyan", min_width=9)

        for i in range(N):
            nombre = f"{EMOJIS[i]} F{i} — {NOMBRES[i]}"
            est, col = ESTADO_STR[snap.estado[i]]
            bar_len = 8
            filled = (
                bar_len     if snap.estado[i] == COMIENDO
                else bar_len // 2 if snap.estado[i] == HAMBRIENTO
                else 0
            )
            barra = f"[{col}]{'█' * filled}{'░' * (bar_len - filled)}[/{col}]"
            estado_r = f"[{col}]{est}[/{col}]\n{barra}"

            iz_idx = self.mesa.izq(i)
            dr_idx = self.mesa.der(i)
            ten_iz = (
                "[green]🍴 Libre[/green]"
                if snap.estado[i] != COMIENDO and snap.estado[iz_idx] != COMIENDO
                else "[red]🥄 Tomado[/red]"
            )
            ten_dr = (
                "[green]🍴 Libre[/green]"
                if snap.estado[i] != COMIENDO and snap.estado[dr_idx] != COMIENDO
                else "[red]🥄 Tomado[/red]"
            )

            table.add_row(nombre, estado_r, ten_iz, ten_dr, str(snap.veces_comio[i]))

        return table


CSS = """
Screen { background: $surface; }

#titulo {
    text-align: center; content-align: center middle;
    color: $accent; text-style: bold;
    padding: 1 2; border: solid $accent;
    margin: 0 1 1 1; width: 1fr; height: auto;
}

#modo-bar {
    border: round $secondary; padding: 0 1; height: 3;
    text-align: center; content-align: center middle;
    margin-bottom: 1;
}

#panel-izq { width: 38%; padding: 0 1; height: 100%; }
#panel-der { width: 62%; padding: 0 1; }
MesaVisual   { border: round $primary;  padding: 1 2; margin-bottom: 1; }
TablaEstados { border: round $success;  padding: 1;   margin-bottom: 1; }
#log-eventos { border: round $warning;  height: 12;   margin-bottom: 1; }
#botones     { height: 3; align: center middle; }
Button       { margin: 0 2; min-width: 18; }
#stats-bar   { border: round $primary-darken-2; padding: 0 1; height: 3; text-align: center; }
"""

ESTADO_BTN_LABELS = {
    "idle":    ("▶ Iniciar",    "success"),
    "running": ("⏸ Pausar",    "primary"),
    "paused":  ("▶▶ Reanudar", "success"),
}


class FilosofosTUI(App):
    CSS = CSS
    TITLE = "Filósofos Comensales"
    BINDINGS = [
        ("q", "quit",   "Salir"),
        ("p", "toggle", "Iniciar / Pausar / Reanudar"),
        ("s", "paso",   "Paso"),
        ("r", "reset",  "Reiniciar"),
    ]

    _btn_estado: str = "idle"

    def __init__(self):
        super().__init__()
        self.mesa = MesaFilosofos()
        self.mesa.log_cb = self._recibir_log
        self._hilos: list[threading.Thread] = []
        self._log_buffer: deque[tuple[int, str]] = deque(maxlen=CFG.max_log_buffer)
        self._lock_log = threading.Lock()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(
            "⚙️ CINCO FILÓSOFOS COMENSALES"
            "[P] Iniciar/Pausar/Reanudar [S] Paso [R] Reiniciar [Q] Salir",
            id="titulo",
        )
        yield Static("", id="modo-bar")

        with Horizontal():
            with Vertical(id="panel-izq"):
                yield MesaVisual(self.mesa, id="mesa-visual")
            with Vertical(id="panel-der"):
                yield TablaEstados(self.mesa, id="tabla-estados")
                yield Static("", id="stats-bar")
                yield RichLog(id="log-eventos", max_lines=400, highlight=True, markup=True)

        with Horizontal(id="botones"):
            yield Button("▶ Iniciar",    id="btn-principal",  variant="success")
            yield Button("⏭ Paso",       id="btn-paso",       variant="warning")
            yield Button("🔄 Reiniciar", id="btn-reiniciar",  variant="error", disabled=True)

        yield Footer()

    def on_mount(self) -> None:
        self._log_app("Sistema listo.")
        self._log_app("[dim]▶ Iniciar arranca libre | ⏭ Paso arranca en modo paso a paso[/dim]")
        self._log_app("[dim]Teclas: [P] toggle principal [S] paso [R] reiniciar [Q] salir[/dim]")
        self.set_interval(CFG.refresco_ui, self._actualizar_pantalla)
        self._actualizar_modo_bar()

    def _actualizar_pantalla(self) -> None:
        if not self.mesa._dirty.is_set():
            return
        self.mesa._dirty.clear()

        self.query_one("#mesa-visual",   MesaVisual).refresh()
        self.query_one("#tabla-estados", TablaEstados).refresh()
        self._actualizar_stats()

        with self._lock_log:
            buffer = list(self._log_buffer)
            self._log_buffer.clear()

        log_widget = self.query_one("#log-eventos", RichLog)
        for i, msg in buffer:
            snap = self.mesa.snapshot()
            color = ESTADO_STR[snap.estado[i]][1]
            log_widget.write(f"[{color}]{EMOJIS[i]} {NOMBRES[i]}[/{color}]: {markup_escape(msg)}")

        if self._btn_estado == "paused":
            self._actualizar_modo_bar()

    def _actualizar_stats(self) -> None:
        snap = self.mesa.snapshot()
        total = sum(snap.veces_comio)
        max_idx = snap.veces_comio.index(max(snap.veces_comio))
        comiendo = sum(1 for e in snap.estado if e == COMIENDO)
        en_cola = self.mesa.eventos_pendientes

        stats = (
            f"[bold white]Total comidas:[/bold white] [cyan]{total}[/cyan] "
            f"[bold white]Más activo:[/bold white] [green]{EMOJIS[max_idx]} {NOMBRES[max_idx]} "
            f"({snap.veces_comio[max_idx]})[/green] "
            f"[bold white]Comiendo:[/bold white] [yellow]{comiendo}/{N}[/yellow] "
            f"[bold white]Esperando paso:[/bold white] [magenta]{en_cola}[/magenta]"
        )
        self.query_one("#stats-bar", Static).update(stats)

    def _actualizar_modo_bar(self) -> None:
        if self._btn_estado == "idle":
            txt = (
                "[dim]● En espera — "
                "▶ Iniciar para correr libre | ⏭ Paso para modo paso a paso[/dim]"
            )
        elif self._btn_estado == "running":
            txt = (
                "[bold green]▶ CORRIENDO[/bold green] · "
                "Ejecución continua · "
                "[bold white]P[/bold white] o [bold white]⏸ Pausar[/bold white] para pausar"
            )
        else:
            prox = self.mesa.proximo_evento()
            txt = (
                f"[bold yellow]⏸ PAUSADO[/bold yellow] · "
                f"[bold white]⏭ Paso[/bold white] o tecla [bold white]S[/bold white] "
                f"para avanzar un evento · "
                f"[magenta]{self.mesa.eventos_pendientes}[/magenta] listo(s) · "
                f"Próximo: [cyan]{prox}[/cyan]"
            )
        self.query_one("#modo-bar", Static).update(txt)

    def _recibir_log(self, i: int, msg: str) -> None:
        with self._lock_log:
            self._log_buffer.append((i, msg))

    def _log_app(self, msg: str) -> None:
        try:
            self.query_one("#log-eventos", RichLog).write(
                f"[bold white]🖥️ SISTEMA:[/bold white] {msg}"
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if   bid == "btn-principal": self._accion_principal()
        elif bid == "btn-paso":      self._accion_paso()
        elif bid == "btn-reiniciar": self._accion_reiniciar()

    def action_toggle(self) -> None: self._accion_principal()
    def action_paso(self)   -> None: self._accion_paso()
    def action_reset(self)  -> None: self._accion_reiniciar()

    def action_quit(self) -> None:
        self.mesa.detener()
        self.exit()

    def _accion_principal(self) -> None:
        if   self._btn_estado == "idle":    self._iniciar(pausado=False)
        elif self._btn_estado == "running": self._pausar()
        else:                               self._reanudar()

    def _accion_paso(self) -> None:
        if   self._btn_estado == "idle":    self._iniciar(pausado=True);  self._avanzar_paso()
        elif self._btn_estado == "running": self._pausar();                self._avanzar_paso()
        else:                               self._avanzar_paso()

    def _accion_reiniciar(self) -> None:
        if self._btn_estado == "idle":
            return

        self.mesa.detener()
        self._hilos.clear()
        self.mesa = MesaFilosofos()
        self.mesa.log_cb = self._recibir_log

        self.query_one("#mesa-visual",   MesaVisual).mesa   = self.mesa
        self.query_one("#tabla-estados", TablaEstados).mesa = self.mesa

        self._btn_estado = "idle"
        self._sincronizar_btn_principal()
        self.query_one("#btn-reiniciar").disabled = True
        self.query_one("#log-eventos", RichLog).clear()

        self._log_app("Sistema reiniciado. Listo para comenzar.")
        self._log_app("[dim]▶ Iniciar para correr libre | ⏭ Paso para modo paso a paso[/dim]")
        self._actualizar_modo_bar()

    def _iniciar(self, pausado: bool) -> None:
        self.mesa._activo = True

        if pausado:
            self.mesa.pausar()
            self._btn_estado = "paused"
            self._log_app("[yellow]⏸ Iniciado en modo PASO A PASO — presiona ⏭ Paso o S.[/yellow]")
        else:
            self._btn_estado = "running"
            self._log_app("[green]▶ Iniciado en modo continuo.[/green]")

        self._sincronizar_btn_principal()
        self.query_one("#btn-reiniciar").disabled = False

        for i in range(N):
            hilo = threading.Thread(
                target=self.mesa.filosofo_ciclo,
                args=(i,),
                daemon=True,
                name=f"Filosofo-{NOMBRES[i]}",
            )
            self._hilos.append(hilo)
            hilo.start()

        self._actualizar_modo_bar()

    def _pausar(self) -> None:
        self.mesa.pausar()
        self._btn_estado = "paused"
        self._log_app(
            "[yellow]⏸ PAUSADO — los filósofos se detienen en < 0.1 s. "
            "Usa ⏭ Paso o tecla S para avanzar evento a evento.[/yellow]"
        )
        self._sincronizar_btn_principal()
        self._actualizar_modo_bar()

    def _reanudar(self) -> None:
        self.mesa.reanudar()
        self._btn_estado = "running"
        self._log_app("[green]▶ REANUDADO — ejecución continua.[/green]")
        self._sincronizar_btn_principal()
        self._actualizar_modo_bar()

    def _avanzar_paso(self) -> None:
        desc = self.mesa.avanzar_paso()
        self._log_app(f"[bold cyan]⏭ PASO:[/bold cyan] {desc}")
        self._actualizar_modo_bar()

    def _sincronizar_btn_principal(self) -> None:
        label, variant = ESTADO_BTN_LABELS[self._btn_estado]
        btn = self.query_one("#btn-principal", Button)
        btn.label = label
        btn.variant = variant
