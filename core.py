from dataclasses import dataclass


@dataclass
class Config:
    n_filosofos: int = 5
    t_pensar_min: float = 1.5
    t_pensar_max: float = 4.0
    t_comer_min: float = 1.0
    t_comer_max: float = 2.5
    refresco_ui: float = 0.25
    feedback_pausa: float = 2.0
    max_log_buffer: int = 200


CFG = Config()
N = CFG.n_filosofos

PENSANDO = 0
HAMBRIENTO = 1
COMIENDO = 2

NOMBRES = ["Platón", "Aristóteles", "Sócrates", "Descartes", "Kant"]
EMOJIS = ["🧠", "📜", "🏛️", "🪶", "⚖️"]

ESTADO_STR = {
    PENSANDO:   ("PENSANDO",   "cyan"),
    HAMBRIENTO: ("HAMBRIENTO", "yellow"),
    COMIENDO:   ("COMIENDO",   "green"),
}


@dataclass
class Snapshot:
    estado: list
    veces_comio: list
