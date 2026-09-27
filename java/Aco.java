// ACO (Ant System) para el TSP — versión OPTIMIZADA en Java.
// Traducción línea a línea de cpp/aco.cpp (run_opt). Arreglos primitivos (double[],
// int[], boolean[]) para evitar objetos por elemento.
// Compilar: javac Aco.java     Uso: java Aco opt <n> <sem_inst> <sem_col> <iters> <m> <k> <esperar>

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.Locale;

public class Aco {
    static long s;
    static long next() {
        s += 0x9E3779B97F4A7C15L;
        long z = s;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
    static double uni() { return (double) (next() >>> 11) * 1.1102230246251565e-16; }
    static int below(int n) { return (int) Long.remainderUnsigned(next(), n); }

    static final double RHO = 0.5, Q = 1.0;

    static int G; static double H;
    static int[] gStart, gItems;
    static int[] lItems, lPos, lCnt;
    static double[] x, y;

    static int celda(double px, double py) {
        int cx = (int) (px * G); if (cx >= G) cx = G - 1;
        int cy = (int) (py * G); if (cy >= G) cy = G - 1;
        return cy * G + cx;
    }
    static boolean antes(double d1, int j1, double d2, int j2) { return d1 < d2 || (d1 == d2 && j1 < j2); }
    static double dist(int a, int b) { double dx = x[a] - x[b], dy = y[a] - y[b]; return Math.sqrt(dx * dx + dy * dy); }

    static void construirRejilla(int n) {
        G = Math.max(1, (int) Math.sqrt((double) n / 2.0));
        H = 1.0 / G;
        int C = G * G;
        gStart = new int[C + 1];
        for (int i = 0; i < n; i++) gStart[celda(x[i], y[i]) + 1]++;
        for (int c = 0; c < C; c++) gStart[c + 1] += gStart[c];
        gItems = new int[n];
        int[] fillp = Arrays.copyOf(gStart, C);
        for (int i = 0; i < n; i++) gItems[fillp[celda(x[i], y[i])]++] = i;
    }

    static void resetLibres(int n) {
        System.arraycopy(gItems, 0, lItems, 0, n);
        for (int c = 0; c < G * G; c++) {
            lCnt[c] = gStart[c + 1] - gStart[c];
            for (int q = gStart[c]; q < gStart[c + 1]; q++) lPos[lItems[q]] = q;
        }
    }
    static void quitar(int c, int cell) {
        int last = gStart[cell] + lCnt[cell] - 1, p = lPos[c], o = lItems[last];
        lItems[p] = o; lPos[o] = p; lItems[last] = c; lPos[c] = last; lCnt[cell]--;
    }

    static int masCercanoLibre(int cur) {
        int c = celda(x[cur], y[cur]); int cx = c % G, cy = c / G;
        int bj = -1; double bd = 0;
        for (int r = 0; r <= G; r++) {
            for (int yy = cy - r; yy <= cy + r; yy++) {
                if (yy < 0 || yy >= G) continue;
                boolean bordeY = (yy == cy - r || yy == cy + r);
                int paso = bordeY ? 1 : 2 * r; if (paso == 0) paso = 1;
                for (int xx = cx - r; xx <= cx + r; xx += paso) {
                    if (xx < 0 || xx >= G) continue;
                    int cc = yy * G + xx;
                    int st = gStart[cc], e = st + lCnt[cc];
                    for (int q = st; q < e; q++) {
                        int j = lItems[q];
                        double d = dist(cur, j);
                        if (bj < 0 || antes(d, j, bd, bj)) { bd = d; bj = j; }
                    }
                }
            }
            if (bj >= 0 && bd <= r * H) break;
        }
        return bj;
    }

    public static void main(String[] a) throws Exception {
        long tIni = System.nanoTime();
        int n = Integer.parseInt(a[1]);
        long si = Long.parseLong(a[2]), sc = Long.parseLong(a[3]);
        int iters = Integer.parseInt(a[4]), m = Integer.parseInt(a[5]), k = Integer.parseInt(a[6]);
        int esperar = Integer.parseInt(a[7]);
        if (k > n - 1) k = n - 1;

        long t0 = System.nanoTime();
        s = si;
        x = new double[n]; y = new double[n];
        for (int i = 0; i < n; i++) { x[i] = uni(); y[i] = uni(); }
        double tInst = (System.nanoTime() - t0) * 1e-9;

        long t1 = System.nanoTime();
        construirRejilla(n);
        int[] cand = new int[n * k];
        double[] eta = new double[n * k];
        {
            double[] bd = new double[k]; int[] bj = new int[k];
            for (int i = 0; i < n; i++) {
                int c = celda(x[i], y[i]); int cx = c % G, cy = c / G;
                int cnt = 0;
                for (int r = 0; r <= G; r++) {
                    for (int yy = cy - r; yy <= cy + r; yy++) {
                        if (yy < 0 || yy >= G) continue;
                        for (int xx = cx - r; xx <= cx + r; xx++) {
                            if (xx < 0 || xx >= G) continue;
                            if (Math.max(Math.abs(xx - cx), Math.abs(yy - cy)) != r) continue;
                            int cc = yy * G + xx;
                            for (int q = gStart[cc]; q < gStart[cc + 1]; q++) {
                                int j = gItems[q]; if (j == i) continue;
                                double d = dist(i, j);
                                if (cnt < k || antes(d, j, bd[k - 1], bj[k - 1])) {
                                    int p = (cnt < k) ? cnt++ : k - 1;
                                    while (p > 0 && antes(d, j, bd[p - 1], bj[p - 1])) { bd[p] = bd[p - 1]; bj[p] = bj[p - 1]; p--; }
                                    bd[p] = d; bj[p] = j;
                                }
                            }
                        }
                    }
                    if (cnt == k && bd[k - 1] <= r * H) break;
                }
                for (int r = 0; r < k; r++) { cand[i * k + r] = bj[r]; eta[i * k + r] = 1.0 / bd[r]; }
            }
        }
        lItems = new int[n]; lPos = new int[n]; lCnt = new int[G * G];
        boolean[] vis = new boolean[n];
        double lnn;
        {
            resetLibres(n);
            int cur = 0; vis[0] = true; quitar(0, celda(x[0], y[0]));
            double L = 0;
            for (int st = 1; st < n; st++) {
                int j = masCercanoLibre(cur);
                L += dist(cur, j); vis[j] = true; quitar(j, celda(x[j], y[j])); cur = j;
            }
            lnn = L + dist(cur, 0);
        }
        double tau0 = (double) m / lnn;
        double[] tau = new double[n * k];
        Arrays.fill(tau, tau0);
        double tSetup = (System.nanoTime() - t1) * 1e-9;

        s = sc;
        int[] tours = new int[m * n];
        double[] L = new double[m];
        double[] buf = new double[k];
        double best = 1e300; int[] bestTour = new int[0];
        double[] curva = new double[iters];
        long fallbacks = 0;
        for (int it = 0; it < iters; it++) {
            for (int ant = 0; ant < m; ant++) {
                int off = ant * n;
                Arrays.fill(vis, false);
                resetLibres(n);
                int cur = below(n);
                tours[off] = cur; vis[cur] = true; quitar(cur, celda(x[cur], y[cur]));
                for (int st = 1; st < n; st++) {
                    int base = cur * k;
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
                        double u = uni() * sum, acc = 0; chosen = -1; int last = -1;
                        for (int r = 0; r < k; r++) {
                            int j = cand[base + r];
                            if (!vis[j]) {
                                acc += buf[r]; last = j;
                                if (acc > u) { chosen = j; break; }
                            }
                        }
                        if (chosen < 0) chosen = last;
                    } else {
                        chosen = masCercanoLibre(cur);
                        fallbacks++;
                    }
                    tours[off + st] = chosen; vis[chosen] = true;
                    quitar(chosen, celda(x[chosen], y[chosen]));
                    cur = chosen;
                }
                double len = 0;
                for (int i = 0; i < n; i++) len += dist(tours[off + i], tours[off + (i + 1) % n]);
                L[ant] = len;
                if (len < best) { best = len; bestTour = Arrays.copyOfRange(tours, off, off + n); }
            }
            for (int e = 0; e < tau.length; e++) tau[e] *= (1.0 - RHO);
            for (int ant = 0; ant < m; ant++) {
                double d = Q / L[ant];
                int off = ant * n;
                for (int i = 0; i < n; i++) {
                    int u = tours[off + i], v = tours[off + (i + 1) % n];
                    int bu = u * k, bv = v * k;
                    for (int r = 0; r < k; r++) if (cand[bu + r] == v) { tau[bu + r] += d; break; }
                    for (int r = 0; r < k; r++) if (cand[bv + r] == u) { tau[bv + r] += d; break; }
                }
            }
            curva[it] = best;
        }
        double tTotal = (System.nanoTime() - t1) * 1e-9;

        long h = 1469598103934665603L;
        for (int c : bestTour) { h ^= (c & 0xFFFFFFFFL); h *= 1099511628211L; }
        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.ROOT,
            "{\"lang\":\"java\",\"version\":\"opt\",\"n\":%d,\"sem_inst\":%d,\"sem_col\":%d,\"iters\":%d,\"m\":%d,\"k\":%d,"
            + "\"lnn\":%.10f,\"best\":%.10f,\"best_bits\":\"%016x\",\"tour_hash\":\"%016x\",\"t_inst\":%.6f,"
            + "\"t_setup\":%.6f,\"t_busqueda\":%.6f,\"t_proceso\":%.6f,\"fallbacks\":%d,\"curva\":[",
            n, si, sc, iters, m, k, lnn, best, Double.doubleToRawLongBits(best), h, tInst, tSetup,
            tTotal - tSetup, (System.nanoTime() - tIni) * 1e-9, fallbacks));
        for (int i = 0; i < iters; i++) { if (i > 0) sb.append(','); sb.append(String.format(Locale.ROOT, "%.8f", curva[i])); }
        sb.append("]}");
        System.out.println(sb);
        System.out.flush();
        if (esperar != 0) new BufferedReader(new InputStreamReader(System.in)).readLine();
    }
}
