"""Compila las implementaciones con las mismas condiciones y registra versiones.

C++  : -O3 (paridad con opt-level=3 de Rust), -ffp-contract=off (sin FMA: mismo
       resultado bit a bit), x86-64 genérico (sin -march=native; ver registro D9).
       Se compila con g++ y con clang++: clang y rustc comparten el optimizador LLVM.
Rust : cargo build --release (opt-level=3, codegen-units=1).
Java : javac.
Uso: python bench/compilar.py
"""
import json
import os
import platform
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = sys.platform.startswith("win")
EXE = ".exe" if WIN else ""
BIN = os.path.join(RAIZ, "bin")

# Si WinLibs se instaló pero la terminal no recargó el PATH, se añade aquí.
for _d in (r"C:\winlibs\mingw64\bin",):
    if WIN and os.path.isdir(_d) and _d.lower() not in os.environ["PATH"].lower():
        os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]


def version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lineas = [l for l in (out.stdout + out.stderr).strip().splitlines()
                  if not l.startswith("Picked up")]
        return lineas[0] if lineas else None
    except Exception:
        return None


def correr(cmd, cwd=None):
    print("  $", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:])
        return False
    return True


def main():
    os.makedirs(BIN, exist_ok=True)
    info = {"plataforma": platform.platform(), "procesador": platform.processor(),
            "python": sys.version.split()[0], "compiladores": {}}
    flags = ["-O3", "-std=c++17", "-ffp-contract=off"] + (["-static"] if WIN else [])
    for nombre, cc in (("cpp-gcc", "g++"), ("cpp-clang", "clang++")):
        if shutil.which(cc) is None:
            print(f"[!] {cc} no encontrado: se omite {nombre}")
            continue
        ok = correr([cc] + flags + ["-o", os.path.join(BIN, f"aco-{nombre}{EXE}"),
                                     os.path.join(RAIZ, "cpp", "aco.cpp")])
        if ok:
            info["compiladores"][nombre] = version([cc, "--version"])
    # Held-Karp (cualquier compilador C++ disponible)
    cc = shutil.which("g++") or shutil.which("clang++")
    if cc:
        correr([cc, "-O3", "-std=c++17", "-o", os.path.join(BIN, f"held_karp{EXE}"),
                os.path.join(RAIZ, "cpp", "held_karp.cpp")] + (["-static"] if WIN else []))
    if shutil.which("cargo"):
        if correr(["cargo", "build", "--release"], cwd=os.path.join(RAIZ, "rust")):
            src = os.path.join(RAIZ, "rust", "target", "release", f"aco{EXE}")
            shutil.copy(src, os.path.join(BIN, f"aco-rust{EXE}"))
            info["compiladores"]["rust"] = version(["rustc", "--version"])
    else:
        print("[!] cargo no encontrado: se omite Rust")
    if shutil.which("javac"):
        if correr(["javac", "-d", BIN, os.path.join(RAIZ, "java", "Aco.java")]):
            info["compiladores"]["java"] = version(["java", "-version"])
    else:
        print("[!] javac no encontrado: se omite Java")
    try:
        import psutil
        info["ram_total_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
        info["nucleos_fisicos"] = psutil.cpu_count(logical=False)
        info["nucleos_logicos"] = psutil.cpu_count(logical=True)
    except ImportError:
        pass
    os.makedirs(os.path.join(RAIZ, "resultados"), exist_ok=True)
    with open(os.path.join(RAIZ, "resultados", "maquina.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    print(json.dumps(info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
