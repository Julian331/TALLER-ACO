# ACO para el TSP: 20, 2 000 y 200 000 ciudades

Ant System (diapositivas de clase) en dos versiones del **mismo algoritmo**:

| versión | representación | memoria | costo por hormiga |
|---|---|---|---|
| `normal` | matrices densas D y T (n × n), ruleta sobre todos los no visitados | O(n²) | O(n²) |
| `opt` | k = 10 vecinos candidatos, feromona solo en esas aristas, rejilla espacial | O(n·k) | ≈ O(n·k) |

Implementado en **C++** (normal + opt), **Python** (normal + opt), **Rust** (opt) y
**Java** (opt). Con la misma semilla los cuatro producen **el mismo tour bit a bit**
(misma aritmética, mismo generador splitmix64), así que las diferencias de tiempo son
de lenguaje y no de algoritmo.

## Estructura

```
cpp/aco.cpp          referencia: versión normal y optimizada
cpp/held_karp.cpp    óptimo exacto para n = 20
rust/src/main.rs     versión optimizada
java/Aco.java        versión optimizada
python/aco.py        versión normal y optimizada (Python puro)
bench/compilar.py    compila todo con las mismas banderas
bench/medir.py       mide una corrida: tiempo y memoria pico desde fuera del proceso
bench/experimentos.py  experimentos A (tabla principal), B (escalamiento), C (convergencia), H (Held-Karp)
bench/analisis.py    tablas y figuras a partir de resultados/
resultados/          una línea JSON por corrida
informe/             informe en LaTeX
```

## Cómo reproducir (Windows, PowerShell, desde esta carpeta)

```
pip install psutil matplotlib
python bench\compilar.py
python bench\experimentos.py --rapido     # prueba de humo, ~1 min
python bench\experimentos.py              # completo, ~15-25 min
python bench\analisis.py
```

Para que las mediciones sean limpias: cerrar navegador y programas pesados, conectar
el portátil a la corriente (si aplica) y no usar el equipo mientras corre.

Una corrida suelta:

```
bin\aco-cpp-gcc.exe opt 200000 200000 1 10 10 10 0
#                   versión n  sem_inst sem_col iters m k esperar
```

## Resultados e informe

- `resultados/` — mediciones en el equipo de entrega (Windows, Ryzen 5 5600G).
- `resultados/resumen.txt` — resumen en texto de todas las cifras.
- `resultados_verificacion_linux/` — las mismas corridas en otro equipo (Linux): los
  70 tours comunes son idénticos bit a bit a los de Windows.
- `bench/masa_probabilidad.py` — fracción de la probabilidad de la ruleta que cae en
  los 10 vecinos más cercanos (explica la mala calidad de la versión normal).
- `informe/informe.pdf` — se regenera con `python bench\analisis.py` y compilando
  `informe/informe.tex` (las cifras entran por `informe/datos.tex`, generado).
