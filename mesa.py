import random
import threading
import time
from collections import deque

from core import CFG, N, PENSANDO, HAMBRIENTO, COMIENDO, NOMBRES, Snapshot


class MesaFilosofos:
    def __init__(self):
        self.estado = [PENSANDO] * N
        self.veces_comio = [0] * N

        self._cond = threading.Condition()
        self._activo = True

        self._paused = threading.Event()
        self._paused.set()
        self._stop_event = threading.Event()

        self._step_lock = threading.Lock()
        self._step_queue: deque[tuple[threading.Event, str]] = deque()

        self.log_cb = None
        self._dirty = threading.Event()
        self._dirty.set()

    def izq(self, i):
        return (i - 1) % N

    def der(self, i):
        return (i + 1) % N

    def snapshot(self) -> Snapshot:
        with self._cond:
            return Snapshot(estado=self.estado[:], veces_comio=self.veces_comio[:])

    @property
    def eventos_pendientes(self) -> int:
        with self._step_lock:
            return len(self._step_queue)

    def _sleep_interruptible(self, i: int, duracion: float, actividad: str) -> bool:
        fin = time.monotonic() + duracion
        ultimo_log = time.monotonic()

        while True:
            ahora = time.monotonic()
            restante = fin - ahora
            if restante <= 0:
                break
            if not self._activo:
                return False

            if not self._paused.is_set():
                if ahora - ultimo_log >= CFG.feedback_pausa:
                    self._log(
                        i,
                        f"[dim][pausado] {actividad} — "
                        f"{(fin - time.monotonic()):.1f}s restantes "
                        f"(presiona ⏭ Paso o ▶▶ Reanudar)[/dim]",
                    )
                    ultimo_log = time.monotonic()
                self._paused.wait(timeout=CFG.feedback_pausa)
                continue

            woken = self._stop_event.wait(timeout=min(restante, 0.5))
            if woken:
                return False

        return self._activo

    def _checkpoint(self, i: int, descripcion: str) -> bool:
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
        with self._step_lock:
            if self._step_queue:
                gate, desc = self._step_queue.popleft()
                gate.set()
                return desc
        return "ningún filósofo en checkpoint aún (espera un momento)"

    def proximo_evento(self) -> str:
        with self._step_lock:
            if self._step_queue:
                return self._step_queue[0][1]
        return "(esperando que un filósofo llegue al checkpoint)"

    def pausar(self):
        self._paused.clear()

    def reanudar(self):
        self._paused.set()
        self._stop_event.clear()
        with self._step_lock:
            for gate, _ in self._step_queue:
                gate.set()
            self._step_queue.clear()

    def _probar(self, i):
        if (
            self.estado[i] == HAMBRIENTO
            and self.estado[self.izq(i)] != COMIENDO
            and self.estado[self.der(i)] != COMIENDO
        ):
            self.estado[i] = COMIENDO
            self._cond.notify_all()

    def tomar_tenedores(self, i):
        with self._cond:
            self.estado[i] = HAMBRIENTO
            self._log(i, "tiene hambre, intenta tomar tenedores...")
            self._probar(i)
            while self.estado[i] != COMIENDO:
                self._cond.wait()

    def poner_tenedores(self, i):
        with self._cond:
            self.estado[i] = PENSANDO
            self._log(i, "terminó de comer, devuelve tenedores")
            self._probar(self.izq(i))
            self._probar(self.der(i))

    def _log(self, i, msg):
        self._dirty.set()
        if self.log_cb:
            self.log_cb(i, msg)

    def filosofo_ciclo(self, i):
        while self._activo:
            if not self._checkpoint(i, f"{NOMBRES[i]} va a PENSAR"):
                break
            self._log(i, "está pensando... 💭")
            if not self._sleep_interruptible(i, random.uniform(CFG.t_pensar_min, CFG.t_pensar_max), "pensando"):
                break

            if not self._checkpoint(i, f"{NOMBRES[i]} quiere pasar a HAMBRIENTO"):
                break
            self.tomar_tenedores(i)
            if not self._activo:
                break

            if not self._checkpoint(i, f"{NOMBRES[i]} va a COMER (obtuvo tenedores)"):
                break
            self._log(i, "¡está COMIENDO! 🍝🍴")
            with self._cond:
                self.veces_comio[i] += 1
            if not self._sleep_interruptible(i, random.uniform(CFG.t_comer_min, CFG.t_comer_max), "comiendo"):
                break

            if not self._checkpoint(i, f"{NOMBRES[i]} va a DEVOLVER tenedores"):
                break
            self.poner_tenedores(i)

    def detener(self):
        self._activo = False
        self._stop_event.set()
        self.reanudar()
        with self._cond:
            for i in range(N):
                self.estado[i] = PENSANDO
            self._cond.notify_all()
        with self._step_lock:
            for gate, _ in self._step_queue:
                gate.set()
            self._step_queue.clear()
