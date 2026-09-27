"""¿Qué fracción de la probabilidad de la ruleta cae en los k vecinos más cercanos?

Primer paso de una hormiga con feromona uniforme (tau = tau0 en todas las aristas):
p_ij ∝ d_ij^(-beta), beta = 2. Se mide, promediando sobre ciudades de origen, la masa
que la ruleta de la versión normal asigna a los k = 10 vecinos más cercanos.
Predicción analítica (plano, densidad n): el peso de las ciudades a distancia en
[r, r+dr] es ∝ n·2πr·r^-2 dr = 2πn dr/r, es decir, cada intervalo logarítmico de
distancia recibe la misma masa -> la fracción en los k más cercanos cae como ~ ln k / ln n.
Uso: python bench/masa_probabilidad.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))
from aco import Rng  # noqa: E402

K = 10


def masa(n, muestras):
    r = Rng(n)
    x, y = [], []
    for _ in range(n):
        x.append(r.uni())
        y.append(r.uni())
    paso = max(1, n // muestras)
    fr = []
    for i in range(0, n, paso):
        w = []
        xi, yi = x[i], y[i]
        for j in range(n):
            if j != i:
                dx = xi - x[j]
                dy = yi - y[j]
                w.append(1.0 / (dx * dx + dy * dy))
        w.sort(reverse=True)
        fr.append(sum(w[:K]) / sum(w))
    return sum(fr) / len(fr), len(fr)


if __name__ == "__main__":
    out = {}
    for n, mu in ((20, 20), (200, 200), (2000, 400), (20000, 100), (200000, 40)):
        f, s = masa(n, mu)
        out[n] = f
        print(f"n={n:>7}: masa en los {K} más cercanos = {f:.3f}  (sobre {s} ciudades de origen)", flush=True)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "resultados", "masa_probabilidad.json"), "w") as fh:
        json.dump(out, fh)
