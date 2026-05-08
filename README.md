# El Problema de los 5 Filósofos Comensales (Dijkstra, 1965)

## 1. Definición del Problema
Formulado originalmente por **Edsger Dijkstra en 1965**, este es un dilema clásico de **sincronización** que ilustra las dificultades de asignar recursos limitados entre varios procesos de forma equitativa y segura [1, 2].

### El Escenario:
*   **Comensales:** Cinco filósofos sentados alrededor de una mesa circular [2-5].
*   **Actividades:** Su vida consiste en alternar periodos de **pensar** y **comer** [3, 4, 6].
*   **Recursos:** Hay cinco platos de arroz (o espaguetis) y solo **cinco palillos** (o tenedores), ubicados uno entre cada par de platos [2-5].
*   **Restricción Crítica:** Debido a la naturaleza del alimento, un filósofo necesita **dos palillos** para poder comer [2-5].

---

## 2. Los Desafíos Técnicos
El problema se utiliza para probar nuevas primitivas de sincronización debido a que presenta dos riesgos fundamentales en sistemas concurrentes:

### A. Interbloqueo (Deadlock)
Ocurre si todos los filósofos deciden comer simultáneamente y cada uno toma el palillo a su izquierda. Al intentar tomar el de su derecha, este ya ha sido tomado por su vecino, provocando que todos esperen eternamente en una **espera circular** [7-10].

### B. Inanición (Starvation)
Incluso si se evita el interbloqueo (por ejemplo, si un filósofo suelta un palillo tras esperar un tiempo), es posible que un filósofo nunca logre comer porque sus vecinos están constantemente alternándose para usar los recursos, haciendo que este "muera de hambre" algorítmicamente [11-14].

---

## 3. Soluciones Propuestas en la Literatura
Las fuentes proponen diversas estrategias para que los programas de cada filósofo se ejecuten sin bloquearse:

1.  **Limitar el número de filósofos:** Permitir que solo un máximo de **cuatro filósofos** se sienten a la mesa simultáneamente, garantizando que al menos uno siempre podrá acceder a dos palillos [15-17].
2.  **Solución Asimétrica:** Que los filósofos con número impar tomen primero su palillo izquierdo y luego el derecho, mientras que los pares lo hagan en orden inverso (primero derecha, luego izquierda) para romper la espera circular [11, 12, 18].
3.  **Uso de Monitores:** Implementar un monitor que controle el estado de cada filósofo (`PENSANDO`, `HAMBRIENTO`, `COMIENDO`). Un filósofo solo puede pasar al estado `COMIENDO` si sus dos vecinos no lo están haciendo [19-26].
4.  **Secciones Críticas:** Permitir que un filósofo tome sus dos palillos solo si ambos están disponibles al mismo tiempo, realizando esta comprobación dentro de una sección crítica de exclusión mutua [11, 16].
