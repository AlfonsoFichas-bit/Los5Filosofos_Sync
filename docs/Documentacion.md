# Documentación del Problema de los Cinco Filósofos Comensales

## Asignatura: Sistemas Operativos

**Estudiante:** [Tu Nombre Aquí]  
**Fecha:** [Fecha Actual]  
**Versión:** 1.0  

---

## Introducción al Problema

El problema de los cinco filósofos comensales plantea cinco filósofos sentados alrededor de una mesa circular, cada uno con un plato de espaguetis y un tenedor entre cada par de platos. Para comer, un filósofo necesita dos tenedores simultáneamente. El desafío es evitar que todos queden bloqueados esperando recursos.

---

## Aplicación de Conceptos de SO en la Solución

### Concurrencia: Simulación con Hilos

Aplicamos el concepto de **procesos concurrentes** utilizando hilos de Python:

```python
# Cada filósofo se ejecuta como un hilo independiente
for i in range(N):
    hilo = threading.Thread(target=self.mesa.filosofo_ciclo, args=(i,))
    hilo.start()
```

Esto simula cómo en SO múltiples procesos comparten recursos del sistema.

### Exclusión Mutua: Protección del Estado Compartido

Para evitar **condiciones de carrera** en el acceso al estado de los filósofos, utilizamos un monitor con `threading.Condition`:

```python
def tomar_tenedores(self, i):
    with self._cond:  # Lock automático del monitor
        self.estado[i] = HAMBRIENTO
        self._probar(i)
        while self.estado[i] != COMIENDO:
            self._cond.wait()  # Espera por condición
```

El `with self._cond` garantiza que solo un hilo modifique el estado a la vez, aplicando **exclusión mutua**.

### Prevención de Deadlock: Condición de Seguridad

Implementamos la condición que rompe el ciclo de espera circular:

```python
def _probar(self, i):
    if (self.estado[i] == HAMBRIENTO and
        self.estado[self.izq(i)] != COMIENDO and
        self.estado[self.der(i)] != COMIENDO):
        self.estado[i] = COMIENDO
        self._cond.notify_all()
```

Esta condición asegura que un filósofo solo coma si **ningún vecino está comiendo**, previniendo que todos esperen indefinidamente.

### Sincronización: Variables de Condición

Las variables de condición permiten esperar por estados específicos:

```python
while self.estado[i] != COMIENDO:
    self._cond.wait()  # Libera lock y espera notificación
```

Cuando un filósofo termina de comer, notifica a todos los que esperan:

```python
def poner_tenedores(self, i):
    with self._cond:
        self.estado[i] = PENSANDO
        self._probar(self.izq(i))  # Verificar vecino izquierdo
        self._probar(self.der(i))  # Verificar vecino derecho
```

### Evitar Starvation: Notificación a Todos

El `notify_all()` despierta a todos los filósofos esperando, permitiendo que el scheduler elija quién progresa primero, garantizando **fairness**.

---

## Análisis de la Solución Implementada

### Cómo se Evita el Deadlock

**Escenario sin solución:** Todos toman tenedor izquierdo simultáneamente, esperando el derecho → deadlock.

**Nuestra solución aplicada:**
1. Filósofo 0 intenta comer: verifica que vecinos (4 y 1) no coman
2. Si condición se cumple, come; sino espera
3. Al terminar, notifica a vecinos 4 y 1
4. Filósofo 2 (no adyacente) puede intentar comer
5. Ciclo continúa, siempre hay progreso

### Exclusión Mutua en Recursos

Los tenedores se representan implícitamente por los estados:
- Si un filósofo está COMIENDO, sus tenedores están en uso
- La condición `estado[vecino] != COMIENDO` garantiza que no se compartan tenedores

### Manejo de Condiciones de Carrera

Sin el monitor, dos filósofos podrían cambiar estados simultáneamente causando inconsistencias. El lock previene esto.

---

## Implementación Detallada

### Ciclo Principal de un Filósofo

```python
def filosofo_ciclo(self, i):
    while self._activo:
        # Fase 1: Pensar (sin recursos)
        time.sleep(random.uniform(CFG.t_pensar_min, CFG.t_pensar_max))

        # Fase 2: Intentar adquirir recursos (exclusión mutua)
        self.tomar_tenedores(i)

        # Fase 3: Usar recursos
        time.sleep(random.uniform(CFG.t_comer_min, CFG.t_comer_max))

        # Fase 4: Liberar recursos y notificar
        self.poner_tenedores(i)
```

Este ciclo demuestra la **alternancia entre pensamiento y alimentación** con sincronización adecuada.

### Control de Ejecución

Para análisis, implementamos pausa/reanudación usando eventos:

```python
def pausar(self):
    self._paused.clear()  # Bloquea progreso

def reanudar(self):
    self._paused.set()    # Permite progreso
    self._cond.notify_all()  # Despierta hilos pausados
```

---

## Verificación de Correctitud

### Propiedades SO Garantizadas

1. **Exclusión Mutua:** Solo un filósofo por tenedor (condición de prueba)
2. **Ausencia de Deadlock:** Condición rompe ciclos de espera
3. **Ausencia de Starvation:** Notificación despierta a todos esperando
4. **Progreso:** Filósofos hambrientos eventualmente comen

### Prueba de Funcionamiento

La implementación compila sin errores y la interfaz permite observar:
- Estados de filósofos en tiempo real
- Contadores de comidas por filósofo
- Logs de eventos de sincronización

---

## Limitaciones y Consideraciones Prácticas

### Limitaciones de la Solución
- Optimizada para 5 filósofos (condición asimétrica)
- No permite paralelismo máximo (solo filósofos no adyacentes comen)

### Aspectos de Implementación en Python
- GIL limita paralelismo real, pero demuestra conceptos
- Hilos simulan procesos concurrentes efectivamente

---

## Conclusión

Esta implementación aplica directamente conceptos de SO como exclusión mutua, sincronización y prevención de deadlocks para resolver el problema clásico. La solución es práctica, observable y demuestra cómo los mecanismos de SO permiten manejar concurrencia de manera segura y eficiente.