"""Ejecuta los experimentos y guarda una línea JSON por corrida en resultados/.

  A  Tabla principal: lenguaje x versión x n ∈ {20, 2000, 200000}, iteraciones fijas.
  B  Escalamiento (C++): tiempo por iteración y memoria contra n, versión normal y optimizada.
  C  Calidad a más largo plazo (C++): curvas de convergencia en 2000 y 200000.
  H  Óptimo exacto de n = 20 por Held-Karp.

Uso:  python bench/experimentos.py            (completo, ~15-25 min)
      python bench/experimentos.py --rapido   (prueba de humo, ~1 min)
      python bench/experimentos.py A B        (solo esos experimentos)
Las corridas ya hechas se saltan (se puede interrumpir y reanudar).
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from medir import medir  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = sys.platform.startswith("win")
EXE = ".exe" if WIN else ""
BIN = os.path.join(RAIZ, "bin")
RES = os.path.join(RAIZ, "resultados")
M, K = 10, 10  # hormigas y vecinos candidatos (registro D6, D11)


def comando(lang, version, n, sem_inst, sem_col, iters):
    args = [version, str(n), str(sem_inst), str(sem_col), str(iters), str(M), str(K), "1"]
    if lang.startswith("cpp") or lang == "rust":
        exe = os.path.join(BIN, f"aco-{lang}{EXE}")
        return [exe] + args if os.path.exists(exe) else None
    if lang == "java":
        return (["java", "-cp", BIN, "Aco"] + args) if os.path.exists(os.path.join(BIN, "Aco.class")) else None
    if lang == "python":
        return [sys.executable, os.path.join(RAIZ, "python", "aco.py")] + args


def lenguajes():
    ls = [l for l in ("cpp-gcc", "cpp-clang", "rust", "java", "python")
          if comando(l, "opt", 20, 1, 1, 1) is not None]
    return ls


def ya_hecho(archivo):
    hechos = set()
    if os.path.exists(archivo):
        with open(archivo, encoding="utf-8") as f:
            for linea in f:
                r = json.loads(linea)
                hechos.add(r["clave"])
    return hechos


def ejecutar(archivo, clave, cmd, extra):
    if clave in ya_hecho(archivo):
        return
    t = time.time()
    try:
        r = medir(cmd)
    except Exception as e:  # se registra el fallo y se sigue
        r = {"error": str(e)[:300]}
    r.update(extra)
    r["clave"] = clave
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(r) + "\n")
    estado = r.get("error") or f"best={r.get('best', 0):.4f}  mem={r.get('mem_pico', 0) / 2**20:.1f} MB"
    print(f"  {clave:<45} {time.time() - t:7.1f} s   {estado}", flush=True)


def exp_A(rapido):
    arch = os.path.join(RES, "A_principal.jsonl")
    iters = {20: 100, 2000: 50, 200000: 10}
    semillas = 5
    if rapido:
        iters = {20: 20, 2000: 3, 200000: 1}
        semillas = 1
    print("== A: tabla principal ==")
    for n in (20, 2000, 200000):
        for s in range(1, semillas + 1):
            for lang in lenguajes():
                versiones = ["normal", "opt"] if (lang.startswith("cpp") or lang == "python") else ["opt"]
                for v in versiones:
                    # Python es ~25-30x más lento: menos repeticiones en los casos caros
                    if lang == "python" and n >= 2000 and s > (1 if (v == "normal" or n == 200000) else 3):
                        continue
                    if v == "normal" and n == 200000 and s > 1:
                        continue
                    cmd = comando(lang, v, n, n, s, iters[n])
                    ejecutar(arch, f"A|{lang}|{v}|{n}|{s}", cmd,
                             {"exp": "A", "lang": lang, "version": v, "n": n, "sem_col": s})


def exp_B(rapido):
    arch = os.path.join(RES, "B_escalamiento.jsonl")
    lang = "cpp-gcc" if "cpp-gcc" in lenguajes() else "cpp-clang"
    ns_normal = [500, 1000, 2000, 4000, 8000, 16000]
    ns_opt = [500, 1000, 2000, 4000, 8000, 16000, 50000, 100000, 200000, 500000, 1000000]
    iters = 5
    if rapido:
        ns_normal, ns_opt, iters = [500, 1000], [500, 1000, 20000], 2
    print("== B: escalamiento ==")
    for v, ns in (("normal", ns_normal), ("opt", ns_opt)):
        for n in ns:
            ejecutar(arch, f"B|{lang}|{v}|{n}", comando(lang, v, n, n, 1, iters),
                     {"exp": "B", "lang": lang, "version": v, "n": n, "sem_col": 1})


def exp_C(rapido):
    arch = os.path.join(RES, "C_convergencia.jsonl")
    lang = "cpp-gcc" if "cpp-gcc" in lenguajes() else "cpp-clang"
    casos = [("normal", 2000, 300, 3), ("opt", 2000, 300, 3), ("opt", 200000, 300, 1)]
    if rapido:
        casos = [("normal", 2000, 5, 1), ("opt", 2000, 5, 1), ("opt", 200000, 2, 1)]
    print("== C: convergencia ==")
    for v, n, it, sem in casos:
        for s in range(1, sem + 1):
            ejecutar(arch, f"C|{lang}|{v}|{n}|{it}|{s}", comando(lang, v, n, n, s, it),
                     {"exp": "C", "lang": lang, "version": v, "n": n, "sem_col": s})


def exp_H(rapido):
    import subprocess
    arch = os.path.join(RES, "H_heldkarp.json")
    if os.path.exists(arch):
        return
    exe = os.path.join(BIN, f"held_karp{EXE}")
    if not os.path.exists(exe):
        print("== H: se omite (held_karp no compilado; falta un compilador de C++) ==")
        return
    print("== H: óptimo exacto n=20 ==")
    t = time.time()
    out = subprocess.run([exe, "20", "20"], capture_output=True, text=True).stdout
    r = json.loads(out)
    r["t"] = time.time() - t
    with open(arch, "w") as f:
        json.dump(r, f)
    print("  ", r)


if __name__ == "__main__":
    rapido = "--rapido" in sys.argv
    if rapido:
        RES = os.path.join(RAIZ, "resultados_rapido")
    os.makedirs(RES, exist_ok=True)
    pedidos = [a for a in sys.argv[1:] if not a.startswith("--")] or ["H", "A", "B", "C"]
    print("lenguajes disponibles:", lenguajes())
    for e in pedidos:
        {"A": exp_A, "B": exp_B, "C": exp_C, "H": exp_H}[e](rapido)
    print("listo. Resultados en", RES)
