"""Mide UNA ejecución desde fuera del proceso: tiempo de pared y memoria pico.

La memoria pico se lee del proceso todavía vivo: cada programa imprime su resultado
y queda esperando una línea por stdin (argumento esperar=1). En ese momento:
  - Windows: psutil -> peak_wset (pico del working set, lo mide el sistema operativo)
  - Linux:   /proc/<pid>/status -> VmHWM (pico de memoria residente)
Así la memoria se mide igual para los cuatro lenguajes, incluyendo la máquina
virtual de Java y el intérprete de Python.
"""
import json
import os
import subprocess
import sys
import time

try:
    import psutil
except ImportError:  # en Linux no es imprescindible
    psutil = None


def memoria_pico(pid):
    if sys.platform.startswith("linux"):
        with open(f"/proc/{pid}/status") as f:
            for linea in f:
                if linea.startswith("VmHWM:"):
                    return int(linea.split()[1]) * 1024
    if psutil is None:
        raise RuntimeError("instale psutil: pip install psutil")
    # En Windows, "java" suele ser un lanzador (javapath\java.exe) que crea la JVM
    # real como proceso hijo: se suma el pico del proceso y de todos sus descendientes.
    p = psutil.Process(pid)
    total = 0
    for q in [p] + p.children(recursive=True):
        try:
            mi = q.memory_info()
            total += getattr(mi, "peak_wset", None) or mi.rss
        except psutil.Error:
            pass
    return total


def medir(cmd, timeout=None):
    """cmd: lista con el comando completo; su último argumento debe ser esperar=1."""
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True)
    linea = p.stdout.readline()
    t_pared = time.perf_counter() - t0
    if not linea:
        err = p.stderr.read()
        p.wait()
        raise RuntimeError(f"sin salida de {cmd}: {err[-800:]}")
    pico = memoria_pico(p.pid)
    p.stdin.write("\n")
    p.stdin.flush()
    p.wait(timeout=60)
    r = json.loads(linea)
    r["t_pared"] = t_pared          # incluye arranque de la JVM / del intérprete
    r["mem_pico"] = pico            # bytes
    return r


if __name__ == "__main__":
    r = medir(sys.argv[1:])
    r.pop("curva", None)
    print(json.dumps(r))
