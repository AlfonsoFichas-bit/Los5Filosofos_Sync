El **Problema de los Filósofos Comensales**, propuesto originalmente por Dijkstra en 1965, es un modelo clásico para ilustrar los desafíos de la **sincronización de procesos** y la gestión de recursos compartidos en sistemas operativos. La solución propuesta por **Andrew S. Tanenbaum** en su libro "Sistemas Operativos Modernos" es una de las más eficientes porque permite el máximo paralelismo posible sin caer en interbloqueos (deadlocks).

Aquí tienes la información veraz y estructurada para que desarrolles tu lógica en Python:

### 1. Variables Globales y Estructuras de Datos
Para implementar la solución de Tanenbaum, necesitas definir los siguientes elementos:

*   **N**: Una constante que representa el número de filósofos (generalmente 5).
*   **Estados de los filósofos**: Un arreglo de tamaño $N$ llamado `estado` que registre en qué situación se encuentra cada uno. Los tres estados posibles son:
    *   **PENSANDO (0)**: El filósofo está realizando actividades que no requieren recursos.
    *   **HAMBRIENTO (1)**: El filósofo ha decidido que quiere comer y está intentando adquirir los tenedores.
    *   **COMIENDO (2)**: El filósofo ha obtenido ambos tenedores y está en su sección crítica.
*   **Semáforos**:
    *   **mutex**: Un semáforo binario inicializado en 1. Se utiliza para garantizar la **exclusión mutua** al acceder o modificar el arreglo de `estado`.
    *   **s[N]**: Un arreglo de $N$ semáforos (uno por filósofo), todos inicializados en 0. Estos se utilizan para bloquear a un filósofo si los tenedores que necesita no están disponibles.

### 2. Macros de Vecindad
Para facilitar el cálculo de quiénes están a los lados de cada filósofo $i$, se utilizan funciones o macros que manejen la mesa circular (aritmética modular):
*   **IZQUIERDO**: $(i + N - 1) \pmod N$
*   **DERECHO**: $(i + 1) \pmod N$

### 3. Lógica de los Procedimientos Principales

#### Función `filosofo(i)`
Cada filósofo ejecuta un ciclo infinito que consiste en:
1.  **Pensar**: Una actividad fuera de la sección crítica.
2.  **tomar_tenedores(i)**: Intento de obtener los recursos.
3.  **Comer**: Uso de los recursos (sección crítica).
4.  **poner_tenedores(i)**: Liberación de los recursos.

#### Función `tomar_tenedores(i)`
Esta función es la entrada a la sección crítica:
1.  Realizar una operación `down` (o `wait`) sobre el semáforo **mutex**.
2.  Cambiar el `estado[i]` a **HAMBRIENTO**.
3.  Llamar a la función auxiliar `test(i)` para verificar si puede comer de inmediato.
4.  Realizar una operación `up` (o `signal`) sobre el semáforo **mutex**.
5.  Realizar una operación `down` sobre su semáforo personal `s[i]`. Si `test(i)` no lo puso a comer, aquí el filósofo quedará bloqueado.

#### Función `poner_tenedores(i)`
Esta función libera los recursos:
1.  Realizar una operación `down` sobre el semáforo **mutex**.
2.  Cambiar el `estado[i]` a **PENSANDO**.
3.  Llamar a `test(IZQUIERDO)` para ver si el vecino de la izquierda estaba esperando y ahora puede comer.
4.  Llamar a `test(DERECHO)` para ver si el vecino de la derecha ahora puede comer.
5.  Realizar una operación `up` sobre el semáforo **mutex**.

#### Función Auxiliar `test(i)`
Es el corazón de la lógica de sincronización:
*   Verifica tres condiciones simultáneas:
    1.  ¿El filósofo $i$ está **HAMBRIENTO**?
    2.  ¿El vecino **IZQUIERDO** no está **COMIENDO**?
    3.  ¿El vecino **DERECHO** no está **COMIENDO**?.
*   Si las tres son ciertas:
    1.  Cambia `estado[i]` a **COMIENDO**.
    2.  Realiza una operación `up` sobre el semáforo personal `s[i]` del filósofo $i$ para desbloquearlo (o evitar que se bloquee si acaba de pedir los tenedores).

### 4. Por qué esta solución funciona
*   **Evita el Deadlock**: A diferencia de la solución ingenua donde todos toman el tenedor izquierdo a la vez, aquí un filósofo solo cambia su estado a "comiendo" si ambos vecinos están inactivos, y todo esto ocurre bajo la protección de un `mutex`.
*   **Máximo Paralelismo**: Permite que dos filósofos coman al mismo tiempo (por ejemplo, el 0 y el 2) siempre que no sean vecinos, optimizando el uso de la CPU.
*   **Evita Inanición (Starvation)**: Aunque esta implementación básica es muy robusta, Tanenbaum menciona que en sistemas con mucha carga un filósofo podría esperar mucho tiempo si sus vecinos se alternan para comer constantemente, aunque en la práctica el orden de llegada de los semáforos suele mitigar esto.