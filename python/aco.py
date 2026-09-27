"""ACO (Ant System) para el TSP — Python puro (sin numpy), versiones normal y optimizada.

Traducción línea a línea de cpp/aco.cpp: mismo generador, mismo orden de operaciones,
mismo tour bit a bit con la misma semilla.
  normal : listas de listas (lo que escribiría cualquiera), matrices n x n.
  opt    : listas de candidatos + rejilla, arreglos planos array('d') / array('i').
Uso: python aco.py <normal|opt> <n> <sem_inst> <sem_col> <iters> <m> <k> <esperar>
"""
import math
import struct
import sys
import time
from array import array

MASK = (1 << 64) - 1
RHO = 0.5
Q = 1.0


class Rng:
    __slots__ = ("s",)

    def __init__(self, seed):
        self.s = seed & MASK

    def next(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & MASK
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def uni(self):
        return (self.next() >> 11) * 1.1102230246251565e-16

    def below(self, n):
        return self.next() % n


def fnv(tour):
    h = 1469598103934665603
    for c in tour:
        h = ((h ^ c) * 1099511628211) & MASK
    return h


def bits(d):
    return struct.unpack("<Q", struct.pack("<d", d))[0]


# ============================================================ NORMAL (densa)
def run_normal(n, x, y, seed, iters, m):
    t0 = time.perf_counter()
    sqrt = math.sqrt
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        Di = D[i]
        xi, yi = x[i], y[i]
        for j in range(n):
            dx = xi - x[j]
            dy = yi - y[j]
            Di[j] = sqrt(dx * dx + dy * dy)
    # vecino más cercano desde 0
    vis = [False] * n
    cur = 0
    vis[0] = True
    L = 0.0
    for _ in range(1, n):
        bj = -1
        bd = 0.0
        Dc = D[cur]
        for j in range(n):
            if not vis[j] and (bj < 0 or Dc[j] < bd):
                bj = j
                bd = Dc[j]
        L += bd
        vis[bj] = True
        cur = bj
    L += D[cur][0]
    lnn = L
    tau0 = m / lnn
    T = [[tau0] * n for _ in range(n)]
    t_setup = time.perf_counter() - t0

    rng = Rng(seed)
    best = 1e300
    best_tour = []
    curva = []
    p = [0.0] * n
    tours = [[0] * n for _ in range(m)]
    Ls = [0.0] * m
    for _it in range(iters):
        for a in range(m):
            vis = [False] * n
            tour = tours[a]
            cur = rng.below(n)
            tour[0] = cur
            vis[cur] = True
            for s in range(1, n):
                Dc = D[cur]
                Tc = T[cur]
                sm = 0.0
                for j in range(n):
                    if not vis[j]:
                        eta = 1.0 / Dc[j]
                        w = Tc[j] * eta * eta
                        p[j] = w
                        sm += w
                r = rng.uni() * sm
                acc = 0.0
                chosen = -1
                last = -1
                for j in range(n):
                    if not vis[j]:
                        acc += p[j]
                        last = j
                        if acc > r:
                            chosen = j
                            break
                if chosen < 0:
                    chosen = last
                tour[s] = chosen
                vis[chosen] = True
                cur = chosen
            ln = 0.0
            for i in range(n):
                ln += D[tour[i]][tour[(i + 1) % n]]
            Ls[a] = ln
            if ln < best:
                best = ln
                best_tour = tour[:]
        f = 1.0 - RHO
        for i in range(n):
            Ti = T[i]
            for j in range(n):
                Ti[j] *= f
        for a in range(m):
            d = Q / Ls[a]
            tour = tours[a]
            for i in range(n):
                u = tour[i]
                v = tour[(i + 1) % n]
                T[u][v] += d
                T[v][u] += d
        curva.append(best)
    return best, best_tour, curva, lnn, t_setup, 0


# ======================================================= OPTIMIZADA (dispersa)
def run_opt(n, x, y, seed, iters, m, k):
    t0 = time.perf_counter()
    sqrt = math.sqrt
    G = max(1, int(math.sqrt(n / 2.0)))
    H = 1.0 / G
    C = G * G

    def celda(px, py):
        cx = int(px * G)
        if cx >= G:
            cx = G - 1
        cy = int(py * G)
        if cy >= G:
            cy = G - 1
        return cy * G + cx

    cel = array("i", [celda(x[i], y[i]) for i in range(n)])  # celda de cada ciudad (caché)
    start = array("i", [0]) * (C + 1)
    for i in range(n):
        start[cel[i] + 1] += 1
    for c in range(C):
        start[c + 1] += start[c]
    items = array("i", [0]) * n
    fillp = array("i", start[:C])
    for i in range(n):
        c = cel[i]
        items[fillp[c]] = i
        fillp[c] += 1

    # k vecinos más cercanos por anillos de la rejilla
    cand = array("i", [0]) * (n * k)
    eta = array("d", [0.0]) * (n * k)
    for i in range(n):
        c = cel[i]
        cx = c % G
        cy = c // G
        xi, yi = x[i], y[i]
        bd = []  # lista ordenada de (d, j), a lo sumo k
        for r in range(G + 1):
            for yy in range(cy - r, cy + r + 1):
                if yy < 0 or yy >= G:
                    continue
                for xx in range(cx - r, cx + r + 1):
                    if xx < 0 or xx >= G:
                        continue
                    if max(abs(xx - cx), abs(yy - cy)) != r:
                        continue
                    cc = yy * G + xx
                    for q in range(start[cc], start[cc + 1]):
                        j = items[q]
                        if j == i:
                            continue
                        dx = xi - x[j]
                        dy = yi - y[j]
                        d = sqrt(dx * dx + dy * dy)
                        if len(bd) < k or (d, j) < bd[-1]:
                            if len(bd) == k:
                                bd.pop()
                            p = len(bd)
                            while p > 0 and (d, j) < bd[p - 1]:
                                p -= 1
                            bd.insert(p, (d, j))
            if len(bd) == k and bd[-1][0] <= r * H:
                break
        base = i * k
        for r in range(k):
            cand[base + r] = bd[r][1]
            eta[base + r] = 1.0 / bd[r][0]

    l_items = array("i", items)
    l_pos = array("i", [0]) * n
    l_cnt = array("i", [0]) * C

    def reset():
        l_items[:] = items
        for c in range(C):
            l_cnt[c] = start[c + 1] - start[c]
        for q in range(n):
            l_pos[l_items[q]] = q

    def quitar(c):
        cell = cel[c]
        last = start[cell] + l_cnt[cell] - 1
        p = l_pos[c]
        o = l_items[last]
        l_items[p] = o
        l_pos[o] = p
        l_items[last] = c
        l_pos[c] = last
        l_cnt[cell] -= 1

    def mas_cercano_libre(cur):
        c = cel[cur]
        cx = c % G
        cy = c // G
        xc, yc = x[cur], y[cur]
        bj = -1
        bd = 0.0
        r = 0
        while r <= G:
            for yy in range(cy - r, cy + r + 1):
                if yy < 0 or yy >= G:
                    continue
                paso = 1 if (yy == cy - r or yy == cy + r) else 2 * r
                if paso == 0:
                    paso = 1
                for xx in range(cx - r, cx + r + 1, paso):
                    if xx < 0 or xx >= G:
                        continue
                    cc = yy * G + xx
                    s = start[cc]
                    for q in range(s, s + l_cnt[cc]):
                        j = l_items[q]
                        dx = xc - x[j]
                        dy = yc - y[j]
                        d = sqrt(dx * dx + dy * dy)
                        if bj < 0 or d < bd or (d == bd and j < bj):
                            bd = d
                            bj = j
            if bj >= 0 and bd <= r * H:
                break
            r += 1
        return bj

    def dist(a, b):
        dx = x[a] - x[b]
        dy = y[a] - y[b]
        return sqrt(dx * dx + dy * dy)

    # vecino más cercano desde 0
    vis = bytearray(n)
    reset()
    cur = 0
    vis[0] = 1
    quitar(0)
    L = 0.0
    for _ in range(1, n):
        j = mas_cercano_libre(cur)
        L += dist(cur, j)
        vis[j] = 1
        quitar(j)
        cur = j
    L += dist(cur, 0)
    lnn = L
    tau0 = m / lnn
    tau = array("d", [tau0]) * (n * k)
    t_setup = time.perf_counter() - t0

    rng = Rng(seed)
    uni = rng.uni
    best = 1e300
    best_tour = []
    curva = []
    tours = [array("i", [0]) * n for _ in range(m)]
    Ls = [0.0] * m
    buf = [0.0] * k
    rk = range(k)
    fallbacks = 0
    cero = bytes(n)
    for _it in range(iters):
        for a in range(m):
            tour = tours[a]
            vis[:] = cero
            reset()
            cur = rng.below(n)
            tour[0] = cur
            vis[cur] = 1
            quitar(cur)
            for s in range(1, n):
                base = cur * k
                sm = 0.0
                for r in rk:
                    j = cand[base + r]
                    if not vis[j]:
                        e = eta[base + r]
                        w = tau[base + r] * e * e
                        buf[r] = w
                        sm += w
                if sm > 0:
                    u = uni() * sm
                    acc = 0.0
                    chosen = -1
                    last = -1
                    for r in rk:
                        j = cand[base + r]
                        if not vis[j]:
                            acc += buf[r]
                            last = j
                            if acc > u:
                                chosen = j
                                break
                    if chosen < 0:
                        chosen = last
                else:
                    chosen = mas_cercano_libre(cur)
                    fallbacks += 1
                tour[s] = chosen
                vis[chosen] = 1
                quitar(chosen)
                cur = chosen
            ln = 0.0
            for i in range(n):
                ln += dist(tour[i], tour[(i + 1) % n])
            Ls[a] = ln
            if ln < best:
                best = ln
                best_tour = list(tour)
        f = 1.0 - RHO
        for e in range(n * k):
            tau[e] *= f
        for a in range(m):
            d = Q / Ls[a]
            tour = tours[a]
            for i in range(n):
                u = tour[i]
                v = tour[(i + 1) % n]
                bu = u * k
                bv = v * k
                for r in rk:
                    if cand[bu + r] == v:
                        tau[bu + r] += d
                        break
                for r in rk:
                    if cand[bv + r] == u:
                        tau[bv + r] += d
                        break
        curva.append(best)
    return best, best_tour, curva, lnn, t_setup, fallbacks


def main():
    a = sys.argv
    t_ini = time.perf_counter()
    ver = a[1]
    n = int(a[2])
    si, sc = int(a[3]), int(a[4])
    iters, m, k, esperar = int(a[5]), int(a[6]), int(a[7]), int(a[8])
    k = min(k, n - 1)
    if ver == "normal" and 2.0 * n * n * 8.0 > 8e9:
        print('{"lang":"python","version":"normal","n":%d,"error":"memoria","bytes_requeridos":%.0f}'
              % (n, 2.0 * n * n * 8.0), flush=True)
        if esperar:
            sys.stdin.readline()
        return
    t0 = time.perf_counter()
    ri = Rng(si)
    x = [0.0] * n
    y = [0.0] * n
    for i in range(n):
        x[i] = ri.uni()
        y[i] = ri.uni()
    if ver == "opt":
        x = array("d", x)
        y = array("d", y)
    t_inst = time.perf_counter() - t0
    t1 = time.perf_counter()
    if ver == "normal":
        best, bt, curva, lnn, t_setup, fb = run_normal(n, x, y, sc, iters, m)
    else:
        best, bt, curva, lnn, t_setup, fb = run_opt(n, x, y, sc, iters, m, k)
    t_tot = time.perf_counter() - t1
    s = ('{"lang":"python","version":"%s","n":%d,"sem_inst":%d,"sem_col":%d,"iters":%d,"m":%d,"k":%d,'
         '"lnn":%.10f,"best":%.10f,"best_bits":"%016x","tour_hash":"%016x","t_inst":%.6f,"t_setup":%.6f,'
         '"t_busqueda":%.6f,"t_proceso":%.6f,"fallbacks":%d,"curva":[%s]}'
         % (ver, n, si, sc, iters, m, 0 if ver == "normal" else k, lnn, best, bits(best), fnv(bt),
            t_inst, t_setup, t_tot - t_setup, time.perf_counter() - t_ini, fb,
            ",".join("%.8f" % c for c in curva)))
    print(s, flush=True)
    if esperar:
        sys.stdin.readline()


if __name__ == "__main__":
    main()
