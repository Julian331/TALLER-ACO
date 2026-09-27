// ACO (Ant System) para el TSP euclidiano — versión de referencia en C++.
//
// Dos versiones del MISMO algoritmo (misma regla de transición, evaporación y depósito):
//   normal : diseño de las diapositivas. Matrices densas D y T (n x n), ruleta sobre
//            todos los nodos no visitados. Memoria O(n^2), costo por hormiga O(n^2).
//   opt    : listas de candidatos (k vecinos más cercanos), feromona solo en esas
//            aristas (n x k), y una rejilla espacial para hallar el vecino no visitado
//            más cercano cuando todos los candidatos ya fueron visitados.
//            Memoria O(n k), costo por hormiga ~O(n k).
//
// Uso: aco <normal|opt> <n> <semilla_instancia> <semilla_colonia> <iteraciones> <m> <k> <esperar>
// Imprime una línea JSON. Si esperar=1, espera una línea por stdin antes de salir
// (el arnés lee la memoria pico del proceso vivo y luego lo libera).
//
// Reglas para que C++, Rust, Java y Python produzcan EXACTAMENTE el mismo tour:
//   - mismo generador (splitmix64) y mismo orden de consumo de números aleatorios;
//   - solo + - * / y sqrt (todas correctamente redondeadas en IEEE-754); nada de pow/exp;
//   - mismo orden de las operaciones de punto flotante; sin contracción a FMA
//     (compilar con -ffp-contract=off).

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

using namespace std;

// ---------------------------------------------------------------- generador
struct Rng {
    uint64_t s;
    explicit Rng(uint64_t seed) : s(seed) {}
    uint64_t next() {
        s += 0x9E3779B97F4A7C15ULL;
        uint64_t z = s;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    double uni() { return (double)(next() >> 11) * 1.1102230246251565e-16; }  // [0,1), 2^-53
    uint32_t below(uint32_t n) { return (uint32_t)(next() % (uint64_t)n); }
};

static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static uint64_t fnv_tour(const vector<int32_t>& t) {
    uint64_t h = 1469598103934665603ULL;
    for (int32_t c : t) { h ^= (uint64_t)(uint32_t)c; h *= 1099511628211ULL; }
    return h;
}

static uint64_t bits(double d) { uint64_t u; memcpy(&u, &d, 8); return u; }

// Parámetros fijos del algoritmo (iguales en los cuatro lenguajes)
static const double RHO = 0.5;  // evaporación (Ant System, Dorigo y Stützle 2004)
static const double Q = 1.0;    // escala del depósito
// alfa = 1 y beta = 2: el peso se calcula como tau * eta * eta (sin pow)

struct Resultado {
    double best = 1e300;
    vector<int32_t> best_tour;
    vector<double> curva;
    double tau0 = 0, lnn = 0;
};

// ======================================================= versión NORMAL (densa)
static void run_normal(int n, const vector<double>& x, const vector<double>& y, uint64_t seed,
                       int iters, int m, Resultado& R, double& t_setup) {
    double t0 = now_s();
    // "código normal": vector<vector<double>> como lo escribiría cualquiera
    vector<vector<double>> D(n, vector<double>(n, 0.0));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            double dx = x[i] - x[j], dy = y[i] - y[j];
            D[i][j] = sqrt(dx * dx + dy * dy);
        }
    // tour del vecino más cercano desde la ciudad 0 -> tau0 = m / L_nn
    {
        vector<char> vis(n, 0);
        int cur = 0; vis[0] = 1; double L = 0;
        for (int s = 1; s < n; s++) {
            int bj = -1; double bd = 0;
            for (int j = 0; j < n; j++)
                if (!vis[j] && (bj < 0 || D[cur][j] < bd)) { bj = j; bd = D[cur][j]; }
            L += bd; vis[bj] = 1; cur = bj;
        }
        L += D[cur][0];
        R.lnn = L;
    }
    R.tau0 = (double)m / R.lnn;
    vector<vector<double>> T(n, vector<double>(n, R.tau0));
    t_setup = now_s() - t0;

    Rng rng(seed);
    vector<vector<int32_t>> tours(m, vector<int32_t>(n));
    vector<double> L(m);
    vector<char> vis(n);
    vector<double> p(n);
    for (int it = 0; it < iters; it++) {
        for (int a = 0; a < m; a++) {
            fill(vis.begin(), vis.end(), 0);
            vector<int32_t>& tour = tours[a];
            int cur = (int)rng.below(n);
            tour[0] = cur; vis[cur] = 1;
            for (int s = 1; s < n; s++) {
                double sum = 0;
                for (int j = 0; j < n; j++) {
                    if (!vis[j]) {
                        double eta = 1.0 / D[cur][j];
                        double w = T[cur][j] * eta * eta;
                        p[j] = w; sum += w;
                    }
                }
                double r = rng.uni() * sum, acc = 0;
                int chosen = -1, last = -1;
                for (int j = 0; j < n; j++) {
                    if (!vis[j]) {
                        acc += p[j]; last = j;
                        if (acc > r) { chosen = j; break; }
                    }
                }
                if (chosen < 0) chosen = last;
                tour[s] = chosen; vis[chosen] = 1; cur = chosen;
            }
            double len = 0;
            for (int i = 0; i < n; i++) len += D[tour[i]][tour[(i + 1) % n]];
            L[a] = len;
            if (len < R.best) { R.best = len; R.best_tour = tour; }
        }
        // evaporación sobre las n^2 aristas
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) T[i][j] *= (1.0 - RHO);
        // depósito de todas las hormigas
        for (int a = 0; a < m; a++) {
            double d = Q / L[a];
            for (int i = 0; i < n; i++) {
                int u = tours[a][i], v = tours[a][(i + 1) % n];
                T[u][v] += d; T[v][u] += d;
            }
        }
        R.curva.push_back(R.best);
    }
}

// ================================================== versión OPTIMIZADA (dispersa)
struct Rejilla {
    int G; double h;
    vector<int32_t> start;  // G*G+1 (formato CSR)
    vector<int32_t> items;  // ciudades ordenadas por celda
    int celda(double px, double py) const {
        int cx = (int)(px * G); if (cx >= G) cx = G - 1;
        int cy = (int)(py * G); if (cy >= G) cy = G - 1;
        return cy * G + cx;
    }
};

static void construir_rejilla(int n, const vector<double>& x, const vector<double>& y, Rejilla& g) {
    g.G = max(1, (int)sqrt((double)n / 2.0));  // ~2 ciudades por celda
    g.h = 1.0 / g.G;
    int C = g.G * g.G;
    g.start.assign(C + 1, 0);
    for (int i = 0; i < n; i++) g.start[g.celda(x[i], y[i]) + 1]++;
    for (int c = 0; c < C; c++) g.start[c + 1] += g.start[c];
    g.items.assign(n, 0);
    vector<int32_t> fillp(g.start.begin(), g.start.end() - 1);
    for (int i = 0; i < n; i++) g.items[fillp[g.celda(x[i], y[i])]++] = i;
}

// ¿(d1,j1) precede a (d2,j2)?  orden canónico: distancia y luego índice
static inline bool antes(double d1, int j1, double d2, int j2) {
    return d1 < d2 || (d1 == d2 && j1 < j2);
}

static void knn(int n, int k, const vector<double>& x, const vector<double>& y, const Rejilla& g,
                vector<int32_t>& cand, vector<double>& eta) {
    cand.assign((size_t)n * k, 0);
    eta.assign((size_t)n * k, 0.0);
    vector<double> bd(k); vector<int32_t> bj(k);
    for (int i = 0; i < n; i++) {
        int c = g.celda(x[i], y[i]); int cx = c % g.G, cy = c / g.G;
        int cnt = 0;
        for (int r = 0; r <= g.G; r++) {
            for (int yy = cy - r; yy <= cy + r; yy++) {
                if (yy < 0 || yy >= g.G) continue;
                for (int xx = cx - r; xx <= cx + r; xx++) {
                    if (xx < 0 || xx >= g.G) continue;
                    if (max(abs(xx - cx), abs(yy - cy)) != r) continue;  // solo el anillo r
                    int cc = yy * g.G + xx;
                    for (int q = g.start[cc]; q < g.start[cc + 1]; q++) {
                        int j = g.items[q]; if (j == i) continue;
                        double dx = x[i] - x[j], dy = y[i] - y[j];
                        double d = sqrt(dx * dx + dy * dy);
                        if (cnt < k || antes(d, j, bd[k - 1], bj[k - 1])) {
                            int p = (cnt < k) ? cnt++ : k - 1;
                            while (p > 0 && antes(d, j, bd[p - 1], bj[p - 1])) { bd[p] = bd[p - 1]; bj[p] = bj[p - 1]; p--; }
                            bd[p] = d; bj[p] = j;
                        }
                    }
                }
            }
            if (cnt == k && bd[k - 1] <= r * g.h) break;
        }
        for (int r = 0; r < k; r++) { cand[(size_t)i * k + r] = bj[r]; eta[(size_t)i * k + r] = 1.0 / bd[r]; }
    }
}

// Estado de "no visitados" por celda, reiniciado por cada hormiga
struct Libres {
    vector<int32_t> items, pos, cnt;
    void reset(const Rejilla& g, int n) {
        items = g.items;
        int C = g.G * g.G;
        if ((int)cnt.size() != C) cnt.resize(C);
        if ((int)pos.size() != n) pos.resize(n);
        for (int c = 0; c < C; c++) {
            cnt[c] = g.start[c + 1] - g.start[c];
            for (int q = g.start[c]; q < g.start[c + 1]; q++) pos[items[q]] = q;
        }
    }
    void quitar(const Rejilla& g, int c, int cell) {
        int last = g.start[cell] + cnt[cell] - 1, p = pos[c], o = items[last];
        items[p] = o; pos[o] = p; items[last] = c; pos[c] = last; cnt[cell]--;
    }
};

static int mas_cercano_libre(int cur, const vector<double>& x, const vector<double>& y,
                             const Rejilla& g, const Libres& L) {
    int c = g.celda(x[cur], y[cur]); int cx = c % g.G, cy = c / g.G;
    int bj = -1; double bd = 0;
    for (int r = 0; r <= g.G; r++) {
        for (int yy = cy - r; yy <= cy + r; yy++) {
            if (yy < 0 || yy >= g.G) continue;
            bool borde_y = (yy == cy - r || yy == cy + r);
            int paso = borde_y ? 1 : 2 * r;  // filas interiores: solo las dos columnas del anillo
            for (int xx = cx - r; xx <= cx + r; xx += (paso == 0 ? 1 : paso)) {
                if (xx < 0 || xx >= g.G) continue;
                int cc = yy * g.G + xx;
                int s = g.start[cc], e = s + L.cnt[cc];
                for (int q = s; q < e; q++) {
                    int j = L.items[q];
                    double dx = x[cur] - x[j], dy = y[cur] - y[j];
                    double d = sqrt(dx * dx + dy * dy);
                    if (bj < 0 || antes(d, j, bd, bj)) { bd = d; bj = j; }
                }
            }
        }
        if (bj >= 0 && bd <= r * g.h) break;
    }
    return bj;
}

static inline double dist(const vector<double>& x, const vector<double>& y, int a, int b) {
    double dx = x[a] - x[b], dy = y[a] - y[b];
    return sqrt(dx * dx + dy * dy);
}

static long long g_fallbacks = 0;

static void run_opt(int n, const vector<double>& x, const vector<double>& y, uint64_t seed,
                    int iters, int m, int k, Resultado& R, double& t_setup) {
    double t0 = now_s();
    Rejilla g; construir_rejilla(n, x, y, g);
    vector<int32_t> cand; vector<double> eta;
    knn(n, k, x, y, g, cand, eta);
    Libres lib;
    vector<char> vis(n);
    // tour del vecino más cercano desde la ciudad 0 (misma definición que la versión normal)
    {
        lib.reset(g, n); fill(vis.begin(), vis.end(), 0);
        int cur = 0; vis[0] = 1; lib.quitar(g, 0, g.celda(x[0], y[0]));
        double L = 0;
        for (int s = 1; s < n; s++) {
            int j = mas_cercano_libre(cur, x, y, g, lib);
            L += dist(x, y, cur, j); vis[j] = 1; lib.quitar(g, j, g.celda(x[j], y[j])); cur = j;
        }
        L += dist(x, y, cur, 0);
        R.lnn = L;
    }
    R.tau0 = (double)m / R.lnn;
    vector<double> tau((size_t)n * k, R.tau0);
    t_setup = now_s() - t0;

    Rng rng(seed);
    vector<int32_t> tours((size_t)m * n);
    vector<double> L(m), buf(k);
    for (int it = 0; it < iters; it++) {
        for (int a = 0; a < m; a++) {
            int32_t* tour = &tours[(size_t)a * n];
            fill(vis.begin(), vis.end(), 0);
            lib.reset(g, n);
            int cur = (int)rng.below(n);
            tour[0] = cur; vis[cur] = 1; lib.quitar(g, cur, g.celda(x[cur], y[cur]));
            for (int s = 1; s < n; s++) {
                size_t base = (size_t)cur * k;
                double sum = 0;
                for (int r = 0; r < k; r++) {
                    int j = cand[base + r];
                    if (!vis[j]) {
                        double w = tau[base + r] * eta[base + r] * eta[base + r];
                        buf[r] = w; sum += w;
                    }
                }
                int chosen;
                if (sum > 0) {
                    double u = rng.uni() * sum, acc = 0; chosen = -1; int last = -1;
                    for (int r = 0; r < k; r++) {
                        int j = cand[base + r];
                        if (!vis[j]) {
                            acc += buf[r]; last = j;
                            if (acc > u) { chosen = j; break; }
                        }
                    }
                    if (chosen < 0) chosen = last;
                } else {
                    chosen = mas_cercano_libre(cur, x, y, g, lib);
                    g_fallbacks++;
                }
                tour[s] = chosen; vis[chosen] = 1;
                lib.quitar(g, chosen, g.celda(x[chosen], y[chosen]));
                cur = chosen;
            }
            double len = 0;
            for (int i = 0; i < n; i++) len += dist(x, y, tour[i], tour[(i + 1) % n]);
            L[a] = len;
            if (len < R.best) { R.best = len; R.best_tour.assign(tour, tour + n); }
        }
        for (size_t e = 0; e < tau.size(); e++) tau[e] *= (1.0 - RHO);
        for (int a = 0; a < m; a++) {
            double d = Q / L[a];
            const int32_t* tour = &tours[(size_t)a * n];
            for (int i = 0; i < n; i++) {
                int u = tour[i], v = tour[(i + 1) % n];
                size_t bu = (size_t)u * k, bv = (size_t)v * k;
                for (int r = 0; r < k; r++) if (cand[bu + r] == v) { tau[bu + r] += d; break; }
                for (int r = 0; r < k; r++) if (cand[bv + r] == u) { tau[bv + r] += d; break; }
            }
        }
        R.curva.push_back(R.best);
    }
}

int main(int argc, char** argv) {
    if (argc < 9) {
        fprintf(stderr, "uso: aco <normal|opt> <n> <sem_inst> <sem_col> <iters> <m> <k> <esperar>\n");
        return 2;
    }
    double t_ini = now_s();
    string ver = argv[1];
    int n = atoi(argv[2]);
    uint64_t si = strtoull(argv[3], 0, 10), sc = strtoull(argv[4], 0, 10);
    int iters = atoi(argv[5]), m = atoi(argv[6]), k = atoi(argv[7]), esperar = atoi(argv[8]);
    if (k > n - 1) k = n - 1;

    if (ver == "normal") {
        // dos matrices n x n de double
        double bytes = 2.0 * (double)n * (double)n * 8.0;
        if (bytes > 8e9) {
            printf("{\"lang\":\"cpp\",\"version\":\"normal\",\"n\":%d,\"error\":\"memoria\",\"bytes_requeridos\":%.0f}\n", n, bytes);
            fflush(stdout);
            if (esperar) { char b[8]; if (!fgets(b, 8, stdin)) {} }
            return 0;
        }
    }

    double t0 = now_s();
    Rng ri(si);
    vector<double> x(n), y(n);
    for (int i = 0; i < n; i++) { x[i] = ri.uni(); y[i] = ri.uni(); }
    double t_inst = now_s() - t0;

    Resultado R; double t_setup = 0;
    double t1 = now_s();
    if (ver == "normal") run_normal(n, x, y, sc, iters, m, R, t_setup);
    else run_opt(n, x, y, sc, iters, m, k, R, t_setup);
    double t_total_alg = now_s() - t1;
    double t_busqueda = t_total_alg - t_setup;

    printf("{\"lang\":\"cpp\",\"version\":\"%s\",\"n\":%d,\"sem_inst\":%llu,\"sem_col\":%llu,"
           "\"iters\":%d,\"m\":%d,\"k\":%d,\"lnn\":%.10f,\"best\":%.10f,\"best_bits\":\"%016llx\","
           "\"tour_hash\":\"%016llx\",\"t_inst\":%.6f,\"t_setup\":%.6f,\"t_busqueda\":%.6f,"
           "\"t_proceso\":%.6f,\"fallbacks\":%lld,\"curva\":[",
           ver.c_str(), n, (unsigned long long)si, (unsigned long long)sc, iters, m,
           ver == "normal" ? 0 : k, R.lnn, R.best, (unsigned long long)bits(R.best),
           (unsigned long long)fnv_tour(R.best_tour), t_inst, t_setup, t_busqueda, now_s() - t_ini,
           g_fallbacks);
    for (size_t i = 0; i < R.curva.size(); i++) printf(i ? ",%.8f" : "%.8f", R.curva[i]);
    printf("]}\n");
    fflush(stdout);
    if (esperar) { char b[8]; if (!fgets(b, 8, stdin)) {} }
    return 0;
}
