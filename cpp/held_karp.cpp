// Óptimo exacto del TSP por programación dinámica (Held-Karp), O(n^2 2^n).
// Genera la MISMA instancia que aco.cpp (mismo generador y semilla) y devuelve
// la longitud óptima. Solo para n <= 22 (memoria 2^(n-1) * (n-1) doubles).
// Uso: held_karp <n> <semilla_instancia>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace std;

struct Rng {
    uint64_t s;
    uint64_t next() {
        s += 0x9E3779B97F4A7C15ULL;
        uint64_t z = s;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    double uni() { return (double)(next() >> 11) * 1.1102230246251565e-16; }
};

int main(int argc, char** argv) {
    int n = atoi(argv[1]);
    Rng r{strtoull(argv[2], 0, 10)};
    vector<double> x(n), y(n);
    for (int i = 0; i < n; i++) { x[i] = r.uni(); y[i] = r.uni(); }
    auto d = [&](int a, int b) { double dx = x[a] - x[b], dy = y[a] - y[b]; return sqrt(dx * dx + dy * dy); };
    int m = n - 1;                      // ciudades 1..n-1; la 0 es el origen fijo
    size_t S = (size_t)1 << m;
    vector<double> dp(S * m, INFINITY);  // dp[mask][j]: camino 0 -> ... -> j que visita mask
    for (int j = 0; j < m; j++) dp[((size_t)1 << j) * m + j] = d(0, j + 1);
    for (size_t mask = 1; mask < S; mask++)
        for (int j = 0; j < m; j++) {
            if (!(mask >> j & 1)) continue;
            double v = dp[mask * m + j];
            if (v == INFINITY) continue;
            for (int k = 0; k < m; k++) {
                if (mask >> k & 1) continue;
                size_t nm = mask | ((size_t)1 << k);
                double c = v + d(j + 1, k + 1);
                if (c < dp[nm * m + k]) dp[nm * m + k] = c;
            }
        }
    double best = INFINITY;
    for (int j = 0; j < m; j++) best = fmin(best, dp[(S - 1) * m + j] + d(j + 1, 0));
    printf("{\"n\":%d,\"sem_inst\":%s,\"optimo\":%.10f}\n", n, argv[2], best);
}
