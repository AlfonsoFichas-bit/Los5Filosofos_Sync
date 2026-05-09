"""
==============================================================
PROBLEMA DE LOS CINCO FILÓSOFOS COMENSALES
Solución: Modelo de Tanenbaum (Estados + Semáforos)
Interfaz: Python + Textual TUI — v9.1
==============================================================

CAMBIOS v9.1 (correcciones respecto a v9):
- [FIX] Log de eventos: se reemplaza el widget Log por RichLog con markup=True.
  Ahora los mensajes del sistema (🖥️ SISTEMA:, ⏭ PASO:, estados de filósofos)
  se muestran con colores y estilos Rich correctamente, en lugar de mostrar
  las etiquetas [bold white], [bold cyan], [green], etc. como texto plano.
- [FIX] write_line() → write(): RichLog no tiene write_line(), usa write().
- [FIX] Contenido dinámico de mensajes de filósofos se escapa con markup_escape()
  para evitar que texto con corchetes (ej. [pausa]) sea interpretado como markup
  Rich y cause MarkupError en tiempo de ejecución.

CAMBIOS v9 (correcciones respecto a v8):
- [FIX] TablaEstados: Ten. Izq / Ten. Der ahora considera también el estado
  del propio filósofo. Si está COMIENDO, sus tenedores se marcan como Tomados
  aunque el vecino no esté comiendo.
- [FIX] _step_queue ahora almacena tuplas (gate, descripcion) en lugar de solo
  el gate. avanzar_paso() retorna la descripción exacta del hilo desbloqueado,
  no el último evento registrado (que podía corresponder a otro filósofo).
  También se elimina el atributo self.ultimo_evento (ya innecesario).
- [FIX] _actualizar_modo_bar usa la descripción del primer elemento de la cola
  en lugar de ultimo_evento para mostrar el próximo checkpoint correcto.
- [FIX] veces_comio[i] += 1 ahora está protegido por self.mutex para garantizar
  thread-safety formal (aunque CPython lo hacía atómico por el GIL).
- [FIX] Modo paso a paso: _sleep_interruptible ahora reporta el tiempo restante
  del sleep al log, dando feedback visual mientras el filósofo "piensa" o "come"
  en pausa, evitando que el usuario crea que el Paso no funcionó.
- [LIMPIEZA] Eliminado el bloque redundante post-tomar_tenedores en filosofo_ciclo
  que reestablecía estado[i]=PENSANDO (detener() ya lo hace).
"""

import threading
import time
import random
import math

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Log, RichLog, Button, Label
from textual.containers import Horizontal, Vertical
from rich.text import Text
from rich.markup import escape as markup_escape
from rich.table import Table
from rich.console import Group

N = 5
PENSANDO = 0
HAMBRIENTO = 1
COMIENDO = 2

NOMBRES = ["Platón", "Aristóteles", "Sócrates", "Descartes", "Kant"]
EMOJIS = ["🧠", "📜", "🏛️", "🪶", "⚖️"]

ESTADO_STR = {
    PENSANDO: ("PENSANDO", "cyan"),
    HAMBRIENTO: ("HAMBRIENTO", "yellow"),
    COMIENDO: ("COMIENDO", "green"),
}


# ─────────────────────────────────────────────
# LÓGICA DE TANENBAUM + CONTROL PAUSA / PASO
# ─────────────────────────────────────────────
class MesaFilosofos:
    def __init__(self):
        self.estado = [PENSANDO] * N
        self.mutex = threading.Lock()
        self.sem = [threading.Semaphore(0) for _ in range(N)]
        self.veces_comio = [0] * N
        self.log_cb = None
        self._activo = True

        # _paused: set → corriendo | clear → pausado/paso-a-paso
        self._paused = threading.Event()
        self._paused.set()

        # [v9] La cola almacena tuplas (gate, descripcion) para que
        # avanzar_paso() devuelva la descripción exacta del hilo desbloqueado.
        self._step_lock = threading.Lock()
        self._step_queue: list[tuple[threading.Event, str]] = []

    def izq(self, i):
        return (i - 1) % N

    def der(self, i):
        return (i + 1) % N

    def _sleep_interruptible(self, i: int, duracion: float, actividad: str) -> bool:
        """
        Duerme 'duracion' segundos de forma interrumpible.
        [v9] En modo pausado, el filósofo no avanza el tiempo y emite un
        mensaje de feedback cada 2 s para que el usuario sepa que está
        esperando (no que el Paso se haya perdido).
        """
        fin = time.monotonic() + duracion
        ultimo_log = time.monotonic()
        while time.monotonic() < fin:
            if not self._activo:
                return False
            if not self._paused.is_set():
                # Pausado: emitir feedback periódico cada 2 s
                ahora = time.monotonic()
                if ahora - ultimo_log >= 2.0:
                    restante = fin - ahora
                    self._log(
                        i,
                        f"[dim][pausado] {actividad} — "
                        f"{restante:.1f}s restantes (presiona ⏭ Paso o ▶▶ Reanudar)[/dim]",
                    )
                    ultimo_log = ahora
            self._paused.wait(timeout=0.1)
        return self._activo

    def _checkpoint(self, i: int, descripcion: str) -> bool:
        """
        Punto de control para el modo paso a paso.
        [v9] Guarda (gate, descripcion) en la cola para que avanzar_paso()
        retorne siempre la descripción exacta del hilo que se desbloquea.
        """
        if self._paused.is_set():
            return self._activo

        my_gate = threading.Event()
        with self._step_lock:
            self._step_queue.append((my_gate, descripcion))

        self._log(i, f"[pausa] esperando paso → {descripcion}")

        while not my_gate.is_set():
            if self._paused.is_set():
                my_gate.set()
                break
            if not self._activo:
                return False
            my_gate.wait(timeout=0.1)

        return self._activo

    def avanzar_paso(self) -> str:
        """
        Desbloquea el primer filósofo en cola y retorna su descripción exacta.
        [v9] La descripción proviene de la tupla (gate, descripcion) almacenada
        al registrarse, no de un atributo compartido que podía ser sobreescrito.
        """
        with self._step_lock:
            if self._step_queue:
                gate, desc = self._step_queue.pop(0)
                gate.set()
                return desc
        return "ningún filósofo en checkpoint aún (espera un momento)"

    def proximo_evento(self) -> str:
        """Retorna la descripción del primer checkpoint pendiente sin desbloquear."""
        with self._step_lock:
            if self._step_queue:
                return self._step_queue[0][1]
        return "(esperando que un filósofo llegue al checkpoint)"

    def pausar(self):
        self._paused.clear()

    def reanudar(self):
        self._paused.set()
        with self._step_lock:
            for gate, _ in self._step_queue:
                gate.set()
            self._step_queue.clear()

    def probar(self, i):
        if (
            self.estado[i] == HAMBRIENTO
            and self.estado[self.izq(i)] != COMIENDO
            and self.estado[self.der(i)] != COMIENDO
        ):
            self.estado[i] = COMIENDO
            self.sem[i].release()

    def tomar_tenedores(self, i):
        with self.mutex:
            self.estado[i] = HAMBRIENTO
            self._log(i, "tiene hambre, intenta tomar tenedores...")
            self.probar(i)
        # IMPORTANTE: la espera del semáforo personal ocurre FUERA del mutex
        # para no bloquear a otros filósofos mientras esperamos.
        self.sem[i].acquire()

    def poner_tenedores(self, i):
        with self.mutex:
            self.estado[i] = PENSANDO
            self._log(i, "terminó de comer, devuelve tenedores")
            self.probar(self.izq(i))
            self.probar(self.der(i))

    def _log(self, i, msg):
        if self.log_cb:
            self.log_cb(i, msg)

    def filosofo_ciclo(self, i):
        while self._activo:
            # ── PENSAR ──────────────────────────────────────────────────
            if not self._checkpoint(i, f"{NOMBRES[i]} va a PENSAR"):
                break
            self._log(i, "está pensando... 💭")
            if not self._sleep_interruptible(i, random.uniform(1.5, 4.0), "pensando"):
                break

            # ── HAMBRIENTO / TOMAR TENEDORES ────────────────────────────
            if not self._checkpoint(i, f"{NOMBRES[i]} quiere pasar a HAMBRIENTO"):
                break
            self.tomar_tenedores(i)

            if not self._activo:
                break

            # ── COMER ────────────────────────────────────────────────────
            if not self._checkpoint(i, f"{NOMBRES[i]} va a COMER (obtuvo tenedores)"):
                break
            self._log(i, "¡está COMIENDO! 🍝🍴")
            # [v9] Incremento protegido por mutex para thread-safety formal
            with self.mutex:
                self.veces_comio[i] += 1
            if not self._sleep_interruptible(i, random.uniform(1.0, 2.5), "comiendo"):
                break

            # ── DEVOLVER TENEDORES ───────────────────────────────────────
            if not self._checkpoint(i, f"{NOMBRES[i]} va a DEVOLVER tenedores"):
                break
            self.poner_tenedores(i)

    def detener(self):
        self._activo = False
        self.reanudar()
        with self.mutex:
            for i in range(N):
                self.estado[i] = PENSANDO
        with self._step_lock:
            for gate, _ in self._step_queue:
                gate.set()
            self._step_queue.clear()
        for sem in self.sem:
            sem.release()


# ─────────────────────────────────────────────
# WIDGET: MESA VISUAL
# ─────────────────────────────────────────────
class MesaVisual(Static):
    POSICIONES = [
        (0, 21), (4, 37), (13, 33), (13, 5), (4, 3),
    ]

    TEN_POS = [
        (2, 31), (9, 37), (15, 21), (9, 5), (2, 13),
    ]

    ANCHO = 49
    ALTURA = 19

    def __init__(self, mesa: MesaFilosofos, **kwargs):
        super().__init__(**kwargs)
        self.mesa = mesa

    def _tenedor_libre(self, t):
        # Tenedor t está entre filósofo t (ten. derecho) y filósofo (t+1)%N (ten. izquierdo)
        return not (
            self.mesa.estado[t] == COMIENDO or
            self.mesa.estado[(t + 1) % N] == COMIENDO
        )

    def render(self):
        estado = self.mesa.estado
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
                    color = colores[estado[i]]
                    ficha = f"{EMOJIS[i]}F{i}"
                    for k, ch in enumerate(ficha):
                        overrides[pc + k] = (ch, color)

            for t, (tr, tc) in enumerate(self.TEN_POS):
                if tr == r:
                    sym = "🍴" if self._tenedor_libre(t) else "🥄"
                    style = "bold green" if self._tenedor_libre(t) else "bold red"
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


# ─────────────────────────────────────────────
# WIDGET: TABLA DE ESTADOS
# ─────────────────────────────────────────────
class TablaEstados(Static):
    def __init__(self, mesa: MesaFilosofos, **kwargs):
        super().__init__(**kwargs)
        self.mesa = mesa

    def render(self):
        table = Table(
            title="[bold white]⚡ Estado de los Filósofos[/bold white]",
            expand=True,
            border_style="bright_black",
            header_style="bold white",
            show_lines=True,
        )

        table.add_column("Filósofo", style="bold white", no_wrap=True, min_width=22)
        table.add_column("Estado", justify="center", min_width=18)
        table.add_column("Ten. Izq", justify="center", min_width=11)
        table.add_column("Ten. Der", justify="center", min_width=11)
        table.add_column("🍝 Comidas", justify="center", style="bold cyan", min_width=9)

        for i in range(N):
            nombre = f"{EMOJIS[i]} F{i} — {NOMBRES[i]}"
            est, col = ESTADO_STR[self.mesa.estado[i]]

            bar_len = 8
            filled = (
                bar_len if self.mesa.estado[i] == COMIENDO
                else bar_len // 2 if self.mesa.estado[i] == HAMBRIENTO
                else 0
            )

            barra = f"[{col}]{'█' * filled}{'░' * (bar_len - filled)}[/{col}]"
            estado_r = f"[{col}]{est}[/{col}]\n{barra}"

            iz_idx = self.mesa.izq(i)
            dr_idx = self.mesa.der(i)

            # [v9] FIX: un tenedor está Tomado si el propio filósofo i está
            # COMIENDO (lo sostiene) O si el vecino que lo comparte está COMIENDO.
            # Antes solo se verificaba el vecino, mostrando "Libre" erróneamente
            # cuando era el propio filósofo quien tenía el tenedor en la mano.
            ten_iz = (
                "[green]🍴 Libre[/green]"
                if self.mesa.estado[i] != COMIENDO and self.mesa.estado[iz_idx] != COMIENDO
                else "[red]🥄 Tomado[/red]"
            )
            ten_dr = (
                "[green]🍴 Libre[/green]"
                if self.mesa.estado[i] != COMIENDO and self.mesa.estado[dr_idx] != COMIENDO
                else "[red]🥄 Tomado[/red]"
            )

            table.add_row(nombre, estado_r, ten_iz, ten_dr, str(self.mesa.veces_comio[i]))

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
MesaVisual { border: round $primary; padding: 1 2; margin-bottom: 1; }
TablaEstados { border: round $success; padding: 1; margin-bottom: 1; }
#log-eventos { border: round $warning; height: 12; margin-bottom: 1; }
#botones { height: 3; align: center middle; }
Button { margin: 0 2; min-width: 18; }
#stats-bar { border: round $primary-darken-2; padding: 0 1; height: 3; text-align: center; }
"""

ESTADO_BTN_LABELS = {
    "idle": ("▶ Iniciar", "success"),
    "running": ("⏸ Pausar", "primary"),
    "paused": ("▶▶ Reanudar", "success"),
}


class FilosofosTUI(App):
    """Filósofos Comensales — Tanenbaum v9.1"""

    CSS = CSS
    TITLE = "Filósofos Comensales — Tanenbaum v9.1"
    BINDINGS = [
        ("q", "quit", "Salir"),
        ("p", "toggle", "Iniciar / Pausar / Reanudar"),
        ("s", "paso", "Paso"),
        ("r", "reset", "Reiniciar"),
    ]

    _btn_estado: str = "idle"

    def __init__(self):
        super().__init__()
        self.mesa = MesaFilosofos()
        self.mesa.log_cb = self._recibir_log
        self._hilos = []
        self._log_buffer = []
        self._lock_log = threading.Lock()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(
            "⚙️ CINCO FILÓSOFOS COMENSALES — Tanenbaum v9.1 | "
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
            yield Button("▶ Iniciar", id="btn-principal", variant="success")
            yield Button("⏭ Paso", id="btn-paso", variant="warning")
            yield Button("🔄 Reiniciar", id="btn-reiniciar", variant="error", disabled=True)

        yield Footer()

    def on_mount(self) -> None:
        self._log_app("Sistema listo.")
        self._log_app("[dim]▶ Iniciar arranca libre | ⏭ Paso arranca directo en modo paso a paso[/dim]")
        self._log_app("[dim]Teclas: [P] toggle principal [S] paso [R] reiniciar [Q] salir[/dim]")
        self.set_interval(0.25, self._actualizar_pantalla)
        self._actualizar_modo_bar()

    def _actualizar_pantalla(self) -> None:
        self.query_one("#mesa-visual", MesaVisual).refresh()
        self.query_one("#tabla-estados", TablaEstados).refresh()
        self._actualizar_stats()

        with self._lock_log:
            buffer = self._log_buffer[:]
            self._log_buffer.clear()

        log_widget = self.query_one("#log-eventos", RichLog)
        for i, msg in buffer:
            color = ESTADO_STR[self.mesa.estado[i]][1]
            log_widget.write(f"[{color}]{EMOJIS[i]} {NOMBRES[i]}[/{color}]: {markup_escape(msg)}")

        if self._btn_estado == "paused":
            self._actualizar_modo_bar()

    def _actualizar_stats(self) -> None:
        total = sum(self.mesa.veces_comio)
        max_idx = self.mesa.veces_comio.index(max(self.mesa.veces_comio))
        comiendo = sum(1 for e in self.mesa.estado if e == COMIENDO)
        en_cola = len(self.mesa._step_queue)

        stats = (
            f"[bold white]Total comidas:[/bold white] [cyan]{total}[/cyan] "
            f"[bold white]Más activo:[/bold white] [green]{EMOJIS[max_idx]} {NOMBRES[max_idx]} "
            f"({self.mesa.veces_comio[max_idx]})[/green] "
            f"[bold white]Comiendo:[/bold white] [yellow]{comiendo}/{N}[/yellow] "
            f"[bold white]Esperando paso:[/bold white] [magenta]{en_cola}[/magenta]"
        )
        self.query_one("#stats-bar", Static).update(stats)

    def _actualizar_modo_bar(self) -> None:
        if self._btn_estado == "idle":
            txt = (
                "[dim]● En espera — "
                "▶ Iniciar para correr libre | ⏭ Paso para arrancar en modo paso a paso[/dim]"
            )
        elif self._btn_estado == "running":
            txt = (
                "[bold green]▶ CORRIENDO[/bold green] · "
                "Ejecución continua · "
                "[bold white]P[/bold white] o [bold white]⏸ Pausar[/bold white] para pausar"
            )
        else:
            en_cola = len(self.mesa._step_queue)
            # [v9] proximo_evento() lee la descripción real del primer gate en cola
            prox = self.mesa.proximo_evento()
            txt = (
                f"[bold yellow]⏸ PAUSADO[/bold yellow] · "
                f"[bold white]⏭ Paso[/bold white] o tecla [bold white]S[/bold white] "
                f"para avanzar un evento · "
                f"[magenta]{en_cola}[/magenta] listo(s) · "
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
        if bid == "btn-principal":
            self._accion_principal()
        elif bid == "btn-paso":
            self._accion_paso()
        elif bid == "btn-reiniciar":
            self._accion_reiniciar()

    def action_toggle(self) -> None:
        self._accion_principal()

    def action_paso(self) -> None:
        self._accion_paso()

    def action_reset(self) -> None:
        self._accion_reiniciar()

    def action_quit(self) -> None:
        self.mesa.detener()
        self.exit()

    def _accion_principal(self) -> None:
        if self._btn_estado == "idle":
            self._iniciar(pausado=False)
        elif self._btn_estado == "running":
            self._pausar()
        else:
            self._reanudar()

    def _accion_paso(self) -> None:
        if self._btn_estado == "idle":
            self._iniciar(pausado=True)
            self._avanzar_paso()
        elif self._btn_estado == "running":
            self._pausar()
            self._avanzar_paso()
        else:
            self._avanzar_paso()

    def _accion_reiniciar(self) -> None:
        if self._btn_estado == "idle":
            return

        self.mesa.detener()
        self._hilos.clear()
        self.mesa = MesaFilosofos()
        self.mesa.log_cb = self._recibir_log

        self.query_one("#mesa-visual", MesaVisual).mesa = self.mesa
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


if __name__ == "__main__":
    app = FilosofosTUI()
    app.run()