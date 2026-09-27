## Lo que se hizo

Dos versiones del mismo algoritmo (misma ruleta, misma evaporación, mismo depósito):

- **normal**: la de clase. La hormiga elige entre todas las ciudades que le faltan.
  Memoria y trabajo crecen con n².
- **optimizada**: la hormiga elige solo entre sus 10 vecinas más cercanas, y la
  feromona se guarda solo para esos caminos. Memoria y trabajo crecen con n.

La optimizada está en C++, Rust, Java y Python; la normal, en C++ y Python. Con la
misma semilla, los cuatro lenguajes dan exactamente el mismo recorrido (lo
comprobamos), así que las diferencias de tiempo son del lenguaje y no del código.

## Lo que se encontro

| | resultado |
|---|---|
| 200 000 ciudades, versión normal | no se puede ejecutar: necesita 640 GB |
| 200 000 ciudades, versión optimizada (C++) | 56.8 MB y 0.4 s por iteración |
| Memoria predicha antes de medir | 277 bytes por ciudad; falló por 0.14 MB como máximo |
| 2 000 ciudades: Python → C++ | 64 veces más rápido |
| 2 000 ciudades: normal → optimizada | 38 veces más rápido |
| 2 000 ciudades: recorrido de la versión normal | peor que el del vecino más cercano (56.5 contra 42.3) |

Con 2 000 ciudades pesó más el lenguaje que el diseño, cosa que no esperábamos. Pero
la ventaja del diseño crece con el tamaño y la del lenguaje no: con 200 000 ciudades
solo la versión optimizada corre, en cualquier lenguaje.

## Cómo correrlo

Hace falta Python 3 (con `pip install psutil matplotlib`), y para compilar el resto:
g++ (probamos WinLibs), Rust y el JDK de Java. Desde esta carpeta, en PowerShell:

```
python bench\compilar.py               # compila C++, Rust y Java
python bench\experimentos.py --rapido  # prueba corta, ~1 min
python bench\experimentos.py           # todo, ~20 min
python bench\analisis.py               # tablas y figuras
```

Una corrida suelta, por ejemplo la optimizada con 200 000 ciudades y 10 iteraciones:

```
bin\aco-cpp-gcc.exe opt 200000 200000 1 10 10 10 0
```

Los argumentos son: versión, ciudades, semilla de la instancia, semilla de las
hormigas, iteraciones, hormigas, vecinos y un 0 final (el 1 lo usa el script de
medición).

## Carpetas

- `cpp/`, `rust/`, `java/`, `python/` — el algoritmo en cada lenguaje. `cpp/held_karp.cpp` calcula el óptimo exacto para 20 ciudades.
- `bench/` — scripts para compilar, medir (tiempo y memoria pico desde fuera del programa) y analizar.
- `resultados/` — una línea por corrida, medidas en un Ryzen 5 5600G con Windows 11.
- `resultados_verificacion_linux/` — las mismas corridas en otro computador; los recorridos coinciden.
- `informe/` — el informe en PDF y su fuente en LaTeX.
