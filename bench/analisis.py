"""Tablas, macros y figuras a partir de resultados/*.jsonl.

Salidas:
  figuras/*.pdf, *.png
  informe/datos.tex             macros con las cifras que cita el informe
  informe/tabla_principal.tex   tabla del experimento A
  informe/tabla_2x2.tex         descomposición diseño x lenguaje
  resultados/resumen.txt        lo mismo en texto plano
Uso: python bench/analisis.py [carpeta_resultados]
"""
import json
import math
import os
import statistics as st
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "resultados")
FIG = os.path.join(RAIZ, "figuras")
INF = os.path.join(RAIZ, "informe")
M, K = 10, 10
MB = 2 ** 20

# identidad fija por lenguaje: color + marcador (legible también en gris)
COLOR = {"python": "#2a78d6", "java": "#eb6834", "cpp-gcc": "#1baf7a",
         "cpp-clang": "#eda100", "rust": "#e87ba4"}
MARCA = {"python": "o", "java": "s", "cpp-gcc": "^", "cpp-clang": "v", "rust": "D"}
NOMBRE = {"python": "Python", "java": "Java", "cpp-gcc": "C++ (g++)",
          "cpp-clang": "C++ (clang++)", "rust": "Rust"}
ORDEN = ["python", "java", "cpp-gcc", "cpp-clang", "rust"]
TINTA, TINTA2, REJ = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": REJ,
    "grid.linewidth": 0.6, "legend.frameon": False, "savefig.bbox": "tight",
})


def cargar(nombre):
    p = os.path.join(RES, nombre)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def bhh(n):
    """Longitud óptima esperada, n puntos uniformes en el cuadrado unidad.
    Ajuste de Cook et al. (TSP Beta, U. Waterloo): 0.712029 + 0.58816/sqrt(n) + 0.568922/n."""
    return math.sqrt(n) * (0.712029 + 0.58816 / math.sqrt(n) + 0.568922 / n)


def mem_pred_opt(n):
    """Bytes de las estructuras de la versión optimizada (C++), contados a mano:
    coordenadas 16n, candidatos 4nk, eta 8nk, tau 8nk, tours 4mn, visitados n,
    rejilla y 'libres' 3*4n, mejor tour 4n, start+cnt de la rejilla ~ 4n."""
    return n * (16 + 20 * K + 4 * M + 1 + 12 + 4 + 4)


def mem_pred_normal(n):
    return 2 * 8 * n * n  # D y T


def pendiente(xs, ys):
    lx = [math.log(v) for v in xs]
    ly = [math.log(v) for v in ys]
    mx, my = st.mean(lx), st.mean(ly)
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)


def med(v):
    return st.median(v) if v else float("nan")


def num(v, d=1):
    """Número con formato LaTeX (coma de miles con \\,)."""
    if v != v:
        return "--"
    s = f"{v:,.{d}f}".replace(",", "\\,")
    return s


def main():
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(INF, exist_ok=True)
    A = [r for r in cargar("A_principal.jsonl") if "best" in r or "bytes_requeridos" in r]
    B = [r for r in cargar("B_escalamiento.jsonl") if "best" in r]
    C = [r for r in cargar("C_convergencia.jsonl") if "best" in r]
    Hp = os.path.join(RES, "H_heldkarp.json")
    opt20 = json.load(open(Hp))["optimo"] if os.path.exists(Hp) else float("nan")
    maq = json.load(open(os.path.join(RES, "maquina.json"))) if os.path.exists(os.path.join(RES, "maquina.json")) else {}
    ref = {20: opt20, 2000: bhh(2000), 200000: bhh(200000)}
    macros = {}
    texto = []

    # ------------------------------------------------------------ Experimento A
    grupos = {}
    for r in A:
        grupos.setdefault((r["n"], r["version"], r["lang"]), []).append(r)
    langs = [l for l in ORDEN if any(k[2] == l for k in grupos)]

    # verificación: mismo tour en todos los lenguajes (por versión, n, semilla)
    identico = {}
    for r in A:
        if "best_bits" in r:
            identico.setdefault((r["version"], r["n"], r["sem_col"]), set()).add((r["best_bits"], r["tour_hash"]))
    n_chk = len(identico)
    n_ok = sum(1 for v in identico.values() if len(v) == 1)
    macros["ToursIdenticos"] = f"{n_ok}"
    macros["ToursComparados"] = f"{n_chk}"
    texto.append(f"Tours idénticos entre lenguajes: {n_ok}/{n_chk} combinaciones (versión, n, semilla)")

    def fila(n, v, l):
        rs = [r for r in grupos.get((n, v, l), []) if "best" in r]
        if not rs:
            return None
        it = rs[0]["iters"]
        return {
            "t_it": med([r["t_busqueda"] / it for r in rs]),
            "t_setup": med([r["t_setup"] for r in rs]),
            "t_pared": med([r["t_pared"] for r in rs]),
            "mem": med([r["mem_pico"] / MB for r in rs]),
            "best": st.mean([r["best"] for r in rs]),
            "best_sd": st.stdev([r["best"] for r in rs]) if len(rs) > 1 else 0.0,
            "reps": len(rs), "iters": it, "lnn": rs[0]["lnn"],
        }

    tab = ["\\begin{tabular}{rllrrrrrr}", "\\toprule",
           "$n$ & versión & lenguaje & corridas & $t$/iter & preparación & pared & memoria pico & brecha \\\\",
           " & & & & (ms) & (ms) & (s) & (MB) & (\\%) \\\\", "\\midrule"]
    for n in (20, 2000, 200000):
        for v in ("normal", "opt"):
            for l in langs:
                f = fila(n, v, l)
                err = [r for r in grupos.get((n, v, l), []) if "bytes_requeridos" in r]
                if f is None and err:
                    gb = err[0]["bytes_requeridos"] / 1e9
                    tab.append(f"{n:,} & {v} & {NOMBRE[l]} & -- & \\multicolumn{{5}}{{l}}{{no ejecutable: requiere {gb:,.0f} GB}} \\\\".replace(",", "\\,"))
                    continue
                if f is None:
                    continue
                brecha = 100 * (f["best"] / ref[n] - 1)
                tab.append(f"{n:,}".replace(",", "\\,") + f" & {v} & {NOMBRE[l]} & {f['reps']} & {num(1000 * f['t_it'], 2)} & "
                           f"{num(1000 * f['t_setup'], 1)} & {num(f['t_pared'], 2)} & {num(f['mem'], 1)} & {num(brecha, 1)} \\\\")
                texto.append(f"n={n:<7} {v:<6} {l:<10} rep={f['reps']} t/it={1000 * f['t_it']:10.3f} ms "
                             f"setup={1000 * f['t_setup']:9.1f} ms pared={f['t_pared']:8.2f} s "
                             f"mem={f['mem']:8.1f} MB best={f['best']:.4f}±{f['best_sd']:.4f} brecha={brecha:+.2f}%")
        tab.append("\\midrule" if n != 200000 else "\\bottomrule")
    tab.append("\\end{tabular}")
    open(os.path.join(INF, "tabla_principal.tex"), "w", encoding="utf-8").write("\n".join(tab) + "\n")

    # macros de A
    def F(n, v, l, campo):
        f = fila(n, v, l)
        return f[campo] if f else float("nan")
    cpp = "cpp-gcc" if "cpp-gcc" in langs else ("cpp-clang" if "cpp-clang" in langs else None)
    macros["IterDosMil"] = str(fila(2000, "opt", langs[0])["iters"]) if fila(2000, "opt", langs[0]) else "--"
    macros["IterDoscientosMil"] = str(fila(200000, "opt", langs[0])["iters"]) if fila(200000, "opt", langs[0]) else "--"
    macros["IterVeinte"] = str(fila(20, "opt", langs[0])["iters"]) if fila(20, "opt", langs[0]) else "--"
    if cpp:
        for v, nombre in (("normal", "Normal"), ("opt", "Opt")):
            macros[f"Mem{nombre}DosMil"] = num(F(2000, v, cpp, "mem"), 1)
            macros[f"Tit{nombre}DosMil"] = num(1000 * F(2000, v, cpp, "t_it"), 1)
        macros["MemOptDoscientosMil"] = num(F(200000, "opt", cpp, "mem"), 1)
        macros["TitOptDoscientosMil"] = num(1000 * F(200000, "opt", cpp, "t_it"), 0)
        macros["SetupOptDoscientosMil"] = num(F(200000, "opt", cpp, "t_setup"), 2)
        macros["MemBaseCpp"] = num(F(20, "opt", cpp, "mem"), 1)
        base = F(20, "opt", cpp, "mem")
        macros["MemPredOptDoscientosMil"] = num(mem_pred_opt(200000) / MB + base, 1)
        macros["MemPredNormalDosMil"] = num(mem_pred_normal(2000) / MB + base, 1)
        macros["MemPredOptDosMil"] = num(mem_pred_opt(2000) / MB + base, 1)
        macros["RatioMemDosMil"] = num((F(2000, "normal", cpp, "mem") - base) / (F(2000, "opt", cpp, "mem") - base), 0)
        # 2x2: diseño x lenguaje en n = 2000
        pn, po = F(2000, "normal", "python", "t_it"), F(2000, "opt", "python", "t_it")
        cn, co = F(2000, "normal", cpp, "t_it"), F(2000, "opt", cpp, "t_it")
        macros["RatioDisenoPython"] = num(pn / po, 0)
        macros["RatioDisenoCpp"] = num(cn / co, 0)
        macros["RatioLenguajeNormal"] = num(pn / cn, 0)
        macros["RatioLenguajeOpt"] = num(po / co, 0)
        macros["RatioTotal"] = num(pn / co, 0)
        macros["RatioLenguajeDoscientosMil"] = num(F(200000, "opt", "python", "t_it") / F(200000, "opt", cpp, "t_it"), 0)
        mpn, mpo = F(2000, "normal", "python", "mem"), F(2000, "opt", "python", "mem")
        mcn, mco = F(2000, "normal", cpp, "mem"), F(2000, "opt", cpp, "mem")
        t2 = ["\\begin{tabular}{lrrr}", "\\toprule",
              " & normal & optimizada & factor del diseño \\\\", "\\midrule",
              f"\\multicolumn{{4}}{{l}}{{\\emph{{tiempo por iteración (ms), $n=2000$}}}} \\\\",
              f"Python & {num(1000 * pn, 1)} & {num(1000 * po, 2)} & {num(pn / po, 0)}$\\times$ \\\\",
              f"C++ & {num(1000 * cn, 1)} & {num(1000 * co, 2)} & {num(cn / co, 0)}$\\times$ \\\\",
              f"factor del lenguaje & {num(pn / cn, 0)}$\\times$ & {num(po / co, 0)}$\\times$ & \\textbf{{{num(pn / co, 0)}$\\times$}} \\\\",
              "\\midrule",
              f"\\multicolumn{{4}}{{l}}{{\\emph{{memoria pico (MB), $n=2000$}}}} \\\\",
              f"Python & {num(mpn, 1)} & {num(mpo, 1)} & {num(mpn / mpo, 0)}$\\times$ \\\\",
              f"C++ & {num(mcn, 1)} & {num(mco, 1)} & {num(mcn / mco, 0)}$\\times$ \\\\",
              f"factor del lenguaje & {num(mpn / mcn, 1)}$\\times$ & {num(mpo / mco, 1)}$\\times$ & \\\\",
              "\\bottomrule", "\\end{tabular}"]
        open(os.path.join(INF, "tabla_2x2.tex"), "w", encoding="utf-8").write("\n".join(t2) + "\n")
        texto.append(f"2x2 tiempo: diseño Py {pn / po:.1f}x, diseño C++ {cn / co:.1f}x, lenguaje normal {pn / cn:.1f}x, "
                     f"lenguaje opt {po / co:.1f}x, total {pn / co:.0f}x")
        texto.append(f"2x2 memoria: Py {mpn:.1f}/{mpo:.1f}  C++ {mcn:.1f}/{mco:.1f} MB")
        # lenguajes contra C++ (g++) en opt
        for l in langs:
            for n in (2000, 200000):
                macros[f"Rel{l.replace('-', '').replace('cpp', 'Cpp').capitalize()}{'DosMil' if n == 2000 else 'DoscientosMil'}"] = \
                    num(F(n, "opt", l, "t_it") / F(n, "opt", cpp, "t_it"), 2)
                macros[f"Mem{l.replace('-', '').replace('cpp', 'Cpp').capitalize()}{'DosMil' if n == 2000 else 'DoscientosMil'}"] = \
                    num(F(n, "opt", l, "mem"), 1)
        # calidad
        macros["LnnDosMil"] = num(F(2000, "opt", cpp, "lnn"), 2)
        macros["LnnDoscientosMil"] = num(F(200000, "opt", cpp, "lnn"), 1)
        macros["BhhDosMil"] = num(bhh(2000), 2)
        macros["BhhDoscientosMil"] = num(bhh(200000), 1)
        macros["BestNormalDosMil"] = num(F(2000, "normal", cpp, "best"), 2)
        macros["BestOptDosMil"] = num(F(2000, "opt", cpp, "best"), 2)
        macros["BestOptDoscientosMil"] = num(F(200000, "opt", cpp, "best"), 1)
        macros["BrechaNormalDosMil"] = num(100 * (F(2000, "normal", cpp, "best") / bhh(2000) - 1), 1)
        macros["BrechaOptDosMil"] = num(100 * (F(2000, "opt", cpp, "best") / bhh(2000) - 1), 1)
        macros["BrechaNnDosMil"] = num(100 * (F(2000, "opt", cpp, "lnn") / bhh(2000) - 1), 1)
        macros["BrechaOptDoscientosMil"] = num(100 * (F(200000, "opt", cpp, "best") / bhh(200000) - 1), 1)
        macros["BrechaNnDoscientosMil"] = num(100 * (F(200000, "opt", cpp, "lnn") / bhh(200000) - 1), 1)
        rs20 = {v: [r for r in grupos.get((20, v, cpp), []) if "best" in r] for v in ("normal", "opt")}
        for v, nombre in (("normal", "Normal"), ("opt", "Opt")):
            ok = sum(1 for r in rs20[v] if abs(r["best"] - opt20) < 1e-9)
            macros[f"Exitos{nombre}Veinte"] = f"{ok}/{len(rs20[v])}"
            macros[f"Brecha{nombre}Veinte"] = num(100 * (st.mean([r['best'] for r in rs20[v]]) / opt20 - 1), 2) if rs20[v] else "--"
        for n_, nn_ in ((2000, "DosMil"), (200000, "DoscientosMil")):
            rs_ = [r for r in grupos.get((n_, "opt", cpp), []) if "best" in r]
            if rs_:
                macros[f"Fallback{nn_}"] = num(100 * st.mean([r["fallbacks"] / (r["iters"] * r["m"] * (r["n"] - 1)) for r in rs_]), 1)
        mp = os.path.join(RES, "masa_probabilidad.json")
        if os.path.exists(mp):
            mdat = json.load(open(mp))
            for n_, nn_ in (("20", "Veinte"), ("200", "Doscientos"), ("2000", "DosMil"), ("20000", "VeinteMil"), ("200000", "DoscientosMil")):
                if n_ in mdat:
                    macros[f"Masa{nn_}"] = f"{mdat[n_]:.2f}"
        macros["OptimoVeinte"] = f"{opt20:.4f}"
        macros["TiempoHK"] = num(json.load(open(Hp)).get("t", float("nan")), 2) if os.path.exists(Hp) else "--"
        macros["MemJavaBase"] = num(F(20, "opt", "java", "mem"), 1) if "java" in langs else "--"
        macros["MemPythonBase"] = num(F(20, "opt", "python", "mem"), 1)
        macros["ParedJavaVeinte"] = num(1000 * F(20, "opt", "java", "t_pared"), 0) if "java" in langs else "--"
        macros["ParedCppVeinte"] = num(1000 * F(20, "opt", cpp, "t_pared"), 0)
        macros["ParedPythonVeinte"] = num(1000 * F(20, "opt", "python", "t_pared"), 0)

    # ------------------------------------------------------------ Experimento B
    if B:
        filas_b = {}
        for r in B:
            filas_b.setdefault(r["n"], {})[r["version"]] = r
        tb = ["\\begin{tabular}{rrrrr}", "\\toprule",
              " & \\multicolumn{2}{c}{memoria pico (MB)} & \\multicolumn{2}{c}{tiempo por iteración (ms)} \\\\",
              "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}",
              "$n$ & normal & optimizada & normal & optimizada \\\\", "\\midrule"]
        for n_ in sorted(filas_b):
            d_ = filas_b[n_]
            def c(v, campo):
                r = d_.get(v)
                if r is None:
                    return "--"
                return num(r["mem_pico"] / MB, 1) if campo == "m" else num(1000 * r["t_busqueda"] / r["iters"], 1)
            tb.append(f"{n_:,}".replace(",", "\\,") + f" & {c('normal','m')} & {c('opt','m')} & {c('normal','t')} & {c('opt','t')} \\\\")
        tb += ["\\bottomrule", "\\end{tabular}"]
        open(os.path.join(INF, "tabla_escalamiento.tex"), "w", encoding="utf-8").write("\n".join(tb) + "\n")
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0))
        base_b = min(r["mem_pico"] for r in B) / MB
        for v, estilo, mk, etiqueta in (("normal", "--", "o", "normal (densa)"), ("opt", "-", "s", "optimizada (dispersa)")):
            rs = sorted([r for r in B if r["version"] == v], key=lambda r: r["n"])
            if not rs:
                continue
            ns = [r["n"] for r in rs]
            ax[0].plot(ns, [r["mem_pico"] / MB for r in rs], estilo, marker=mk, color=TINTA if v == "normal" else "#2a78d6",
                       lw=1.6, ms=5, label=etiqueta)
            ax[1].plot(ns, [1000 * r["t_busqueda"] / r["iters"] for r in rs], estilo, marker=mk,
                       color=TINTA if v == "normal" else "#2a78d6", lw=1.6, ms=5, label=etiqueta)
            # ajuste donde las estructuras dominan a la memoria base del proceso
            grandes = [r for r in rs if r["n"] >= (2000 if v == "normal" else 50000)]
            if len(grandes) >= 2:
                sm = pendiente([r["n"] for r in grandes], [r["mem_pico"] / MB - base_b for r in grandes])
                stt = pendiente([r["n"] for r in grandes], [r["t_busqueda"] / r["iters"] for r in grandes])
                nom = "Normal" if v == "normal" else "Opt"
                macros[f"PendMem{nom}"] = num(sm, 2)
                macros[f"PendTiempo{nom}"] = num(stt, 2)
                macros[f"NMax{nom}"] = num(max(ns), 0)
                macros[f"NMinAjuste{nom}"] = num(min(r["n"] for r in grandes), 0)
                texto.append(f"Escalamiento {v}: pendiente memoria {sm:.2f}, tiempo {stt:.2f} (n>={min(r['n'] for r in grandes)}, hasta {max(ns)})")
        # predicciones
        xs = [500 * 1.25 ** i for i in range(0, 50) if 500 * 1.25 ** i <= 1.2e6]
        ax[0].plot([x for x in xs if x <= 60000], [mem_pred_normal(x) / MB + base_b for x in xs if x <= 60000], ":",
                   color=TINTA2, lw=1.2, label="predicción $16n^2$ B")
        ax[0].plot(xs, [mem_pred_opt(x) / MB + base_b for x in xs], ":", color="#2a78d6", lw=1.2,
                   label=f"predicción {mem_pred_opt(1)}$n$ B")
        ram = maq.get("ram_total_gb", 16) * 1024
        ax[0].axhline(ram, color="#e34948", lw=1)
        ax[0].text(600, ram * 1.25, f"RAM del equipo ({ram / 1024:.0f} GB)", color=TINTA2, fontsize=8)
        ax[0].axvline(200000, color=TINTA2, lw=0.8, ls="-.")
        ax[1].axvline(200000, color=TINTA2, lw=0.8, ls="-.")
        for a in ax:
            a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("número de ciudades $n$")
        ax[0].set_ylabel("memoria pico (MB)")
        ax[1].set_ylabel("tiempo por iteración (ms)")
        ax[0].set_title("Memoria", fontsize=9, loc="left", color=TINTA)
        ax[1].set_title("Tiempo (10 hormigas por iteración)", fontsize=9, loc="left", color=TINTA)
        ax[0].legend(fontsize=7, loc="upper left")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(os.path.join(FIG, f"escalamiento.{ext}"), dpi=200)
        plt.close(fig)
        texto.append(f"Memoria predicha opt: {mem_pred_opt(1)} B por ciudad")
        macros["BytesPorCiudad"] = str(mem_pred_opt(1))
        # extrapolación de la versión normal a 200 000 con la pendiente medida
        rn = sorted([r for r in B if r["version"] == "normal"], key=lambda r: r["n"])
        if rn:
            ult = rn[-1]
            t200 = ult["t_busqueda"] / ult["iters"] * (200000 / ult["n"]) ** 2
            macros["ExtrapTiempoNormalDoscientosMil"] = num(t200 / 60, 0)
            macros["NMaxNormalMedido"] = num(ult["n"], 0)
            texto.append(f"Extrapolación normal a 200000: {t200 / 60:.1f} min por iteración")
        # error máximo de la predicción de memoria (versión optimizada, n >= 50000)
        base_c = min(r["mem_pico"] for r in B if r["version"] == "opt") / MB
        errs = [abs(r["mem_pico"] / MB - (mem_pred_opt(r["n"]) / MB + base_c)) for r in B if r["version"] == "opt"]
        macros["ErrMaxPredMem"] = num(max(errs), 1)
        texto.append(f"Error máximo de la predicción de memoria (opt): {max(errs):.2f} MB")

    # ------------------------------------------------------------ Figura lenguajes
    if cpp:
        fig, ax = plt.subplots(2, 2, figsize=(7.2, 4.4))
        for fila_i, n in enumerate((2000, 200000)):
            etiquetas, tt, mm, cols, hatch = [], [], [], [], []
            for v in ("normal", "opt"):
                for l in langs:
                    f = fila(n, v, l)
                    if f is None:
                        continue
                    etiquetas.append(f"{NOMBRE[l]}" + (" · normal" if v == "normal" else ""))
                    tt.append(1000 * f["t_it"]); mm.append(f["mem"]); cols.append(COLOR[l])
                    hatch.append("////" if v == "normal" else "")
            if not etiquetas:
                continue
            y = list(range(len(etiquetas)))[::-1]
            for j, (vals, a, unidad) in enumerate(((tt, ax[fila_i][0], "ms"), (mm, ax[fila_i][1], "MB"))):
                bars = a.barh(y, vals, color=cols, height=0.7, edgecolor="white", linewidth=1)
                for b_, h_ in zip(bars, hatch):
                    b_.set_hatch(h_)
                a.set_xscale("log")
                a.set_yticks(y)
                a.set_yticklabels(etiquetas if j == 0 else [""] * len(y), fontsize=7.5)
                for yi, v_ in zip(y, vals):
                    a.text(v_ * 1.08, yi, f"{v_:,.1f}" if v_ < 100 else f"{v_:,.0f}", va="center", fontsize=7, color=TINTA2)
                a.set_xlim(min(vals) / 1.5, max(vals) * 4)
                a.grid(axis="y", visible=False)
                a.set_title(f"$n = {n:,}$".replace(",", "\\,") + (" — tiempo por iteración (ms)" if j == 0 else " — memoria pico (MB)"),
                            fontsize=8.5, loc="left", color=TINTA)
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(os.path.join(FIG, f"lenguajes.{ext}"), dpi=200)
        plt.close(fig)

    # ------------------------------------------------------------ Experimento C
    if C:
        fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
        for i, n in enumerate((2000, 200000)):
            a = ax[i]
            for v, colr, est in (("normal", TINTA, "--"), ("opt", "#2a78d6", "-")):
                rs = [r for r in C if r["n"] == n and r["version"] == v]
                if not rs:
                    continue
                L = min(len(r["curva"]) for r in rs)
                medc = [st.median([r["curva"][t] for r in rs]) for t in range(L)]
                a.plot(range(1, L + 1), medc, est, color=colr, lw=1.8,
                       label=("normal" if v == "normal" else "optimizada")
                       + (f" (mediana de {len(rs)} semillas)" if len(rs) > 1 else " (1 semilla)"))
                if len(rs) > 1:
                    a.fill_between(range(1, L + 1), [min(r["curva"][t] for r in rs) for t in range(L)],
                                   [max(r["curva"][t] for r in rs) for t in range(L)], color=colr, alpha=0.12, lw=0)
                nom = "Normal" if v == "normal" else "Opt"
                nn = "DosMil" if n == 2000 else "DoscientosMil"
                macros[f"ConvFinal{nom}{nn}"] = num(medc[-1], 2 if n == 2000 else 1)
                macros[f"ConvIters{nom}{nn}"] = str(L)
                lnn = rs[0]["lnn"]
                cruce = next((t + 1 for t, c in enumerate(medc) if c < lnn), None)
                macros[f"ConvCruceNN{nom}{nn}"] = f"en la iteración {cruce}" if cruce else "en ninguna de las iteraciones"
                macros[f"ConvTiempo{nom}{nn}"] = num(st.median([r["t_busqueda"] for r in rs]), 0)
                texto.append(f"Convergencia n={n} {v}: final {medc[-1]:.3f}, cruza NN en iteración {cruce}, "
                             f"t_busqueda {st.median([r['t_busqueda'] for r in rs]):.1f} s")
            lnn = [r for r in C if r["n"] == n][0]["lnn"]
            a.axhline(lnn, color="#e34948", lw=1, ls=":")
            a.axhline(bhh(n), color="#008300", lw=1, ls="-.")
            a.text(1.05, lnn, " vecino más\n cercano", color=TINTA2, fontsize=7, va="center", transform=a.get_yaxis_transform())
            a.text(1.05, bhh(n), " óptimo\n esperado", color=TINTA2, fontsize=7, va="center", transform=a.get_yaxis_transform())
            a.set_xscale("log")
            a.set_xlabel("iteración")
            a.set_ylabel("mejor longitud encontrada")
            a.set_title(f"$n = {n:,}$".replace(",", "\\,"), fontsize=9, loc="left", color=TINTA)
            lo = bhh(n) * 0.97
            hi = lnn * (1.45 if n == 2000 else 1.25)  # recorta las primeras iteraciones (fuera de escala)
            a.set_ylim(lo, hi)
            a.legend(fontsize=7, loc="center right" if n == 2000 else "upper right")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(os.path.join(FIG, f"convergencia.{ext}"), dpi=200)
        plt.close(fig)

    # ------------------------------------------------------------ máquina
    macros["Procesador"] = maq.get("procesador", "").replace("_", "\\_") or "--"
    macros["Plataforma"] = maq.get("plataforma", "").replace("_", "\\_") or "--"
    for k_, v_ in maq.get("compiladores", {}).items():
        macros["Version" + k_.replace("-", "").replace("cpp", "Cpp").capitalize()] = v_.replace("_", "\\_").replace("#", "\\#")
    macros["VersionPython"] = maq.get("python", "--")
    macros["HayClang"] = "1" if "cpp-clang" in langs else "0"
    macros.setdefault("VersionCppclang", "--")

    with open(os.path.join(INF, "datos.tex"), "w", encoding="utf-8") as f:
        f.write("% generado por bench/analisis.py — no editar a mano\n")
        for k_, v_ in sorted(macros.items()):
            f.write(f"\\newcommand{{\\{k_}}}{{{v_}}}\n")
    with open(os.path.join(RES, "resumen.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(texto) + "\n\n" + "\n".join(f"{k_} = {v_}" for k_, v_ in sorted(macros.items())) + "\n")
    print("\n".join(texto))


if __name__ == "__main__":
    main()
