## EL PROBLEMA DE LOS CINCO FILÓSOFOS COMENSALES

En 1965, Dijkstra formuló y luego resolvió un problema de sincronización que denominó el problema de los filósofos comensales. Es un dilema clásico de sincronización en Sistemas operativos. El problema se puede plantear de forma muy sencilla de la siguiente manera: cinco filósofos están sentados alrededor de una mesa circular. Cada filósofo tiene un plato de espaguetis. Los espaguetis son tan resbaladizos que un filósofo necesita dos tenedores (recursos) para comerlos. Entre cada par de platos hay un tenedor. Si todos toman el tenedor izquierdo simultáneamente, ocurre un **bloqueo mutuo (deadlock)**. El dibujo de la mesa se ilustra en la Figura 1. La vida de un filósofo consiste en alternar periodos de comer y pensar. Cuando un filósofo tiene suficiente hambre, intenta coger sus tenedores de la izquierda.

```
Figura 1 La hora del almuerzo en el departamento de filosofía.
```
y a la derecha, uno a la vez, el orden no importa. Si logra coger dos tenedores, come un rato, luego los deja y continúa pensando. La pregunta fundamental es: ¿se puede escribir un programa para cada filósofo que haga lo que debe hacer y nunca se quede atascado? Supongamos que los cinco filósofos cogen sus tenedores izquierdos simultáneamente. Ninguno podrá coger sus tenedores derechos y se producirá un punto muerto.

**Aspectos importantes o principales del Problema:**

- **Escenario:** 5 filósofos, 5 platos de spaghetti y 5 tenedores en una mesa redonda.
- **Mecánica:** Para comer, un filósofo necesita tomar tanto el tenedor de su izquierda como el de su
    derecha.
- **Conflicto (Deadlock):** Si todos toman su tenedor izquierdo al mismo tiempo, ninguno puede comer y
    todos esperan indefinidamente.
- **Inanición (Starvation):** El riesgo de que un filósofo nunca consiga ambos tenedores y muera de
    hambre.
- **Soluciones:** Implementar algoritmos, como el uso de semáforos, asegurar que al menos uno tome
    primero el tenedor derecho, o permitir comer a un número impar de filósofos.

Este ejercicio ilustra la concurrencia, el acceso compartido a recursos limitados y cómo evitar que procesos se detengan mutuamente en Sistemas Operativos.
El problema de los filósofos comensales es útil para modelar procesos que compiten por el acceso exclusivo a un número limitado de recursos, como en los dispositivos de entrada/salida (E/S). 