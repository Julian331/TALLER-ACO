// ACO (Ant System) para el TSP — versión OPTIMIZADA en Rust.
// Traducción línea a línea de cpp/aco.cpp (run_opt). Rust seguro: todos los accesos
// a arreglos llevan comprobación de límites (es parte de lo que se mide).
// Uso: aco opt <n> <sem_inst> <sem_col> <iters> <m> <k> <esperar>

use std::io::{BufRead, Write};
use std::time::Instant;

struct Rng { s: u64 }
impl Rng {
    fn next(&mut self) -> u64 {
        self.s = self.s.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }
    fn uni(&mut self) -> f64 { (self.next() >> 11) as f64 * 1.1102230246251565e-16 }
    fn below(&mut self, n: usize) -> usize { (self.next() % n as u64) as usize }
}

const RHO: f64 = 0.5;
const Q: f64 = 1.0;

struct Rejilla { g: usize, h: f64, start: Vec<i32>, items: Vec<i32> }
impl Rejilla {
    fn celda(&self, px: f64, py: f64) -> usize {
        let g = self.g as i64;
        let mut cx = (px * self.g as f64) as i64; if cx >= g { cx = g - 1; }
        let mut cy = (py * self.g as f64) as i64; if cy >= g { cy = g - 1; }
        (cy * g + cx) as usize
    }
}

fn construir_rejilla(n: usize, x: &[f64], y: &[f64]) -> Rejilla {
    let g = std::cmp::max(1, ((n as f64) / 2.0).sqrt() as usize);
    let mut r = Rejilla { g, h: 1.0 / g as f64, start: vec![0; g * g + 1], items: vec![0; n] };
    for i in 0..n { let c = r.celda(x[i], y[i]); r.start[c + 1] += 1; }
    for c in 0..g * g { r.start[c + 1] += r.start[c]; }
    let mut fillp: Vec<i32> = r.start[..g * g].to_vec();
    for i in 0..n { let c = r.celda(x[i], y[i]); r.items[fillp[c] as usize] = i as i32; fillp[c] += 1; }
    r
}

#[inline]
fn antes(d1: f64, j1: i32, d2: f64, j2: i32) -> bool { d1 < d2 || (d1 == d2 && j1 < j2) }

#[inline]
fn dist(x: &[f64], y: &[f64], a: usize, b: usize) -> f64 {
    let dx = x[a] - x[b]; let dy = y[a] - y[b];
    (dx * dx + dy * dy).sqrt()
}

fn knn(n: usize, k: usize, x: &[f64], y: &[f64], g: &Rejilla) -> (Vec<i32>, Vec<f64>) {
    let mut cand = vec![0i32; n * k];
    let mut eta = vec![0f64; n * k];
    let mut bd = vec![0f64; k]; let mut bj = vec![0i32; k];
    let gg = g.g as i64;
    for i in 0..n {
        let c = g.celda(x[i], y[i]) as i64; let (cx, cy) = (c % gg, c / gg);
        let mut cnt = 0usize;
        for r in 0..=gg {
            for yy in (cy - r)..=(cy + r) {
                if yy < 0 || yy >= gg { continue; }
                for xx in (cx - r)..=(cx + r) {
                    if xx < 0 || xx >= gg { continue; }
                    if std::cmp::max((xx - cx).abs(), (yy - cy).abs()) != r { continue; }
                    let cc = (yy * gg + xx) as usize;
                    for q in g.start[cc]..g.start[cc + 1] {
                        let j = g.items[q as usize];
                        if j as usize == i { continue; }
                        let d = dist(x, y, i, j as usize);
                        if cnt < k || antes(d, j, bd[k - 1], bj[k - 1]) {
                            let mut p = if cnt < k { cnt += 1; cnt - 1 } else { k - 1 };
                            while p > 0 && antes(d, j, bd[p - 1], bj[p - 1]) { bd[p] = bd[p - 1]; bj[p] = bj[p - 1]; p -= 1; }
                            bd[p] = d; bj[p] = j;
                        }
                    }
                }
            }
            if cnt == k && bd[k - 1] <= r as f64 * g.h { break; }
        }
        for r in 0..k { cand[i * k + r] = bj[r]; eta[i * k + r] = 1.0 / bd[r]; }
    }
    (cand, eta)
}

struct Libres { items: Vec<i32>, pos: Vec<i32>, cnt: Vec<i32> }
impl Libres {
    fn reset(&mut self, g: &Rejilla) {
        self.items.copy_from_slice(&g.items);
        for c in 0..g.g * g.g {
            self.cnt[c] = g.start[c + 1] - g.start[c];
            for q in g.start[c]..g.start[c + 1] { self.pos[self.items[q as usize] as usize] = q; }
        }
    }
    fn quitar(&mut self, g: &Rejilla, c: usize, cell: usize) {
        let last = (g.start[cell] + self.cnt[cell] - 1) as usize;
        let p = self.pos[c] as usize; let o = self.items[last];
        self.items[p] = o; self.pos[o as usize] = p as i32;
        self.items[last] = c as i32; self.pos[c] = last as i32; self.cnt[cell] -= 1;
    }
}

fn mas_cercano_libre(cur: usize, x: &[f64], y: &[f64], g: &Rejilla, l: &Libres) -> usize {
    let gg = g.g as i64;
    let c = g.celda(x[cur], y[cur]) as i64; let (cx, cy) = (c % gg, c / gg);
    let mut bj: i32 = -1; let mut bd = 0f64;
    for r in 0..=gg {
        for yy in (cy - r)..=(cy + r) {
            if yy < 0 || yy >= gg { continue; }
            let borde_y = yy == cy - r || yy == cy + r;
            let paso = if borde_y { 1 } else { 2 * r };
            let paso = if paso == 0 { 1 } else { paso };
            let mut xx = cx - r;
            while xx <= cx + r {
                if xx >= 0 && xx < gg {
                    let cc = (yy * gg + xx) as usize;
                    let s = g.start[cc]; let e = s + l.cnt[cc];
                    for q in s..e {
                        let j = l.items[q as usize];
                        let d = dist(x, y, cur, j as usize);
                        if bj < 0 || antes(d, j, bd, bj) { bd = d; bj = j; }
                    }
                }
                xx += paso;
            }
        }
        if bj >= 0 && bd <= r as f64 * g.h { break; }
    }
    bj as usize
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 9 { eprintln!("uso: aco opt <n> <sem_inst> <sem_col> <iters> <m> <k> <esperar>"); std::process::exit(2); }
    let t_ini = Instant::now();
    let n: usize = a[2].parse().unwrap();
    let si: u64 = a[3].parse().unwrap(); let sc: u64 = a[4].parse().unwrap();
    let iters: usize = a[5].parse().unwrap(); let m: usize = a[6].parse().unwrap();
    let mut k: usize = a[7].parse().unwrap(); let esperar: i32 = a[8].parse().unwrap();
    if k > n - 1 { k = n - 1; }

    let t0 = Instant::now();
    let mut ri = Rng { s: si };
    let mut x = vec![0f64; n]; let mut y = vec![0f64; n];
    for i in 0..n { x[i] = ri.uni(); y[i] = ri.uni(); }
    let t_inst = t0.elapsed().as_secs_f64();

    let t1 = Instant::now();
    let g = construir_rejilla(n, &x, &y);
    let (cand, eta) = knn(n, k, &x, &y, &g);
    let mut lib = Libres { items: vec![0; n], pos: vec![0; n], cnt: vec![0; g.g * g.g] };
    let mut vis = vec![false; n];
    let lnn = {
        lib.reset(&g);
        let mut cur = 0usize; vis[0] = true; lib.quitar(&g, 0, g.celda(x[0], y[0]));
        let mut l = 0f64;
        for _ in 1..n {
            let j = mas_cercano_libre(cur, &x, &y, &g, &lib);
            l += dist(&x, &y, cur, j); vis[j] = true; lib.quitar(&g, j, g.celda(x[j], y[j])); cur = j;
        }
        l + dist(&x, &y, cur, 0)
    };
    let tau0 = m as f64 / lnn;
    let mut tau = vec![tau0; n * k];
    let t_setup = t1.elapsed().as_secs_f64();

    let mut rng = Rng { s: sc };
    let mut tours = vec![0i32; m * n];
    let mut lens = vec![0f64; m];
    let mut buf = vec![0f64; k];
    let mut best = 1e300f64; let mut best_tour: Vec<i32> = Vec::new();
    let mut curva: Vec<f64> = Vec::with_capacity(iters);
    let mut fallbacks: i64 = 0;
    for _it in 0..iters {
        for ant in 0..m {
            let tour = &mut tours[ant * n..(ant + 1) * n];
            for v in vis.iter_mut() { *v = false; }
            lib.reset(&g);
            let mut cur = rng.below(n);
            tour[0] = cur as i32; vis[cur] = true; lib.quitar(&g, cur, g.celda(x[cur], y[cur]));
            for s in 1..n {
                let base = cur * k;
                let mut sum = 0f64;
                for r in 0..k {
                    let j = cand[base + r] as usize;
                    if !vis[j] {
                        let w = tau[base + r] * eta[base + r] * eta[base + r];
                        buf[r] = w; sum += w;
                    }
                }
                let chosen: usize;
                if sum > 0.0 {
                    let u = rng.uni() * sum; let mut acc = 0f64;
                    let mut ch: i64 = -1; let mut last: i64 = -1;
                    for r in 0..k {
                        let j = cand[base + r] as usize;
                        if !vis[j] {
                            acc += buf[r]; last = j as i64;
                            if acc > u { ch = j as i64; break; }
                        }
                    }
                    chosen = if ch < 0 { last as usize } else { ch as usize };
                } else {
                    chosen = mas_cercano_libre(cur, &x, &y, &g, &lib);
                    fallbacks += 1;
                }
                tour[s] = chosen as i32; vis[chosen] = true;
                lib.quitar(&g, chosen, g.celda(x[chosen], y[chosen]));
                cur = chosen;
            }
            let mut len = 0f64;
            for i in 0..n { len += dist(&x, &y, tour[i] as usize, tour[(i + 1) % n] as usize); }
            lens[ant] = len;
            if len < best { best = len; best_tour = tour.to_vec(); }
        }
        for t in tau.iter_mut() { *t *= 1.0 - RHO; }
        for ant in 0..m {
            let d = Q / lens[ant];
            let tour = &tours[ant * n..(ant + 1) * n];
            for i in 0..n {
                let u = tour[i] as usize; let v = tour[(i + 1) % n] as usize;
                let (bu, bv) = (u * k, v * k);
                for r in 0..k { if cand[bu + r] as usize == v { tau[bu + r] += d; break; } }
                for r in 0..k { if cand[bv + r] as usize == u { tau[bv + r] += d; break; } }
            }
        }
        curva.push(best);
    }
    let t_total = t1.elapsed().as_secs_f64();

    let mut h: u64 = 1469598103934665603;
    for &c in &best_tour { h ^= c as u32 as u64; h = h.wrapping_mul(1099511628211); }
    let mut s = format!(
        "{{\"lang\":\"rust\",\"version\":\"opt\",\"n\":{},\"sem_inst\":{},\"sem_col\":{},\"iters\":{},\"m\":{},\"k\":{},\"lnn\":{:.10},\"best\":{:.10},\"best_bits\":\"{:016x}\",\"tour_hash\":\"{:016x}\",\"t_inst\":{:.6},\"t_setup\":{:.6},\"t_busqueda\":{:.6},\"t_proceso\":{:.6},\"fallbacks\":{},\"curva\":[",
        n, si, sc, iters, m, k, lnn, best, best.to_bits(), h, t_inst, t_setup, t_total - t_setup,
        t_ini.elapsed().as_secs_f64(), fallbacks);
    for (i, c) in curva.iter().enumerate() { if i > 0 { s.push(','); } s.push_str(&format!("{:.8}", c)); }
    s.push_str("]}");
    let out = std::io::stdout();
    let mut o = out.lock(); writeln!(o, "{}", s).unwrap(); o.flush().unwrap(); drop(o);
    if esperar != 0 { let mut l = String::new(); let _ = std::io::stdin().lock().read_line(&mut l); }
}
