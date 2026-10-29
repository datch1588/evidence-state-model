#!/usr/bin/env python3
"""Чисельна перевірка теорем статті «Модель стану свідчень…» (позначення давнішої редакції рукопису, див. README).

Перевіряє на синтетичних даних:
  T1a  межу min{1, n_max*alpha} теореми 1(а) і її досяжність (лінійне програмування);
  T1b  тест на ставках з дод. А.1: частку хибних проходжень за нульової гіпотези,
       мінімальну кількість перевірних текстів і що ламається без умови ізоляції;
  T2   обидві нерівності теореми 2 на випадкових потоках текстів
       і непокращуваність сталої на конструкції з дод. А.2 (точно й методом Монте-Карло);
  T3   межі теореми 3(б), твердження 3(а), формулу r~, табл. 4 і приклад 2;
  T4   рівносильності теореми 4(а) і критерій 4(б);
  P    властивості 1-4 і лему 1 на випадкових множинах тверджень.

Запуск: python3 scripts/theorem_checks.py --out results.json > out_theorems.txt
Потрібні numpy і scipy. Усі генератори мають фіксовані зерна; прогін триває кілька хвилин.
Час прогону й версії бібліотек пишуться лише в results.json, тож вихід можна порівняти
з expected/theorem_checks.txt.
"""
import argparse
import itertools
import json
import math
import random
import sys
import time
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog

RESULTS = {}


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- T1a
def t1a():
    """Теорема 1(а): sup Pr(F3>=1 | N>0) за E[F/N | N>0] <= alpha і N <= n_max."""
    rows = []
    for n_max in (1, 2, 3, 6, 10):
        # типи текстів: (N, F, f3), 1 <= N <= n_max, 0 <= F <= N, f3 in {0,1}, f3 <= [F >= 1]
        types = [(N, F, f3) for N in range(1, n_max + 1) for F in range(0, N + 1)
                 for f3 in (0, 1) if f3 <= (F >= 1)]
        c = -np.array([t[2] for t in types], dtype=float)          # максимізуємо Pr(F3>=1)
        a_ub = np.array([[t[1] / t[0] for t in types]])            # E[F/N] <= alpha
        a_eq = np.ones((1, len(types)))
        for alpha in (0.01, 0.05, 0.1, 0.2, 0.3, 0.5):
            res = linprog(c, A_ub=a_ub, b_ub=[alpha], A_eq=a_eq, b_eq=[1.0],
                          bounds=[(0, None)] * len(types), method="highs")
            lp = -res.fun
            bound = min(1.0, n_max * alpha)
            rows.append({"n_max": n_max, "alpha": alpha, "lp_sup": lp, "bound": bound,
                         "diff": lp - bound})
    max_abs = max(abs(r["diff"]) for r in rows)

    # випадкові розподіли: межа ніде не порушується
    rng = np.random.default_rng(11)
    worst = 0.0
    n_checked = 0
    for _ in range(20000):
        n_max = int(rng.integers(1, 11))
        types = [(N, F, f3) for N in range(1, n_max + 1) for F in range(0, N + 1)
                 for f3 in (0, 1) if f3 <= (F >= 1)]
        k = int(rng.integers(1, min(8, len(types)) + 1))
        idx = rng.choice(len(types), size=k, replace=False)
        p = rng.dirichlet(np.ones(k))
        ef = sum(p[j] * types[i][1] / types[i][0] for j, i in enumerate(idx))
        pr3 = sum(p[j] * types[i][2] for j, i in enumerate(idx))
        bound = min(1.0, n_max * ef)
        if bound > 0:
            worst = max(worst, pr3 / bound)
        elif pr3 > 0:
            worst = float("inf")
        n_checked += 1
    RESULTS["T1a"] = {"lp_rows": rows, "lp_max_abs_diff": max_abs,
                      "random_distributions": n_checked,
                      "random_max_ratio_to_bound": worst,
                      "ok": bool(max_abs < 1e-9 and worst <= 1 + 1e-12)}
    log(f"T1a: max |LP - min(1,n_max*alpha)| = {max_abs:.2e}; "
        f"випадкові розподіли: max Pr/межа = {worst:.6f}")


# ---------------------------------------------------------------- T1b
def betting_pass(losses, alpha3, kappa, thr, strategy):
    """Чи проходить поріг тест на ставках на рядках losses (масив reps x n)."""
    reps, n = losses.shape
    nu_max = kappa / (1 - alpha3)
    log_c = np.zeros(reps)
    passed = np.zeros(reps, dtype=bool)
    s1 = np.zeros(reps)
    s2 = np.zeros(reps)
    log_thr = math.log(thr)
    for i in range(n):
        if strategy == "max":
            nu = np.full(reps, nu_max)
        elif strategy == "half":
            nu = np.full(reps, 0.5 * nu_max)
        elif strategy == "agrapa":
            # передбачувана ставка на кшталт aGRAPA (Waudby-Smith, Ramdas, 2024): лише за попередніми втратами
            k = max(i, 1)
            mean = (s1 + alpha3) / (i + 1)          # згладжене середнє з апріорним alpha3
            var = np.maximum(s2 / k - (s1 / k) ** 2, 0.0) if i > 0 else np.full(reps, 0.25)
            gap = alpha3 - mean
            nu = np.clip(gap / (var + gap ** 2 + 1e-12), 0.0, nu_max)
        else:
            raise ValueError(strategy)
        x = losses[:, i]
        log_c += np.log1p(nu * (alpha3 - x))
        passed |= log_c >= log_thr
        s1 += x
        s2 += x * x
    return passed


def t1b():
    J, delta, kappa = 3, 0.1, 0.75
    thr = J / delta
    rng = np.random.default_rng(22)

    # мінімальна кількість перевірних текстів: формула і пряме обчислення капіталу
    nmin = {}
    for a3 in (0.1, 0.2, 0.3, 0.0625):
        nu_max = kappa / (1 - a3)
        formula = math.ceil(math.log(J / delta) / math.log(1 + nu_max * a3))
        c, k = 1.0, 0
        while c < thr:
            k += 1
            c *= 1 + nu_max * a3
        nmin[str(a3)] = {"formula": formula, "direct": k}

    # частка хибних проходжень за R = alpha3 (найгірший випадок нульової гіпотези)
    reps = 40000
    null_rows = []
    for a3 in (0.0625, 0.1, 0.2, 0.3):
        for n in (50, 100, 300):
            losses = (rng.random((reps, n)) < a3).astype(float)
            for strat in ("max", "half", "agrapa"):
                p = betting_pass(losses, a3, kappa, thr, strat).mean()
                se = math.sqrt(p * (1 - p) / reps)
                null_rows.append({"alpha3": a3, "n_cal": n, "strategy": strat,
                                  "pass_rate": p, "se": se, "limit": delta / J})
    worst_null = max(r["pass_rate"] - 3 * r["se"] for r in null_rows)

    # повна процедура: J = 3 пороги з ризиками, що всі >= alpha3; частка вибору поганого порога
    full_rows = []
    for a3 in (0.1, 0.2):
        for risks in ((a3, a3, a3), (a3, a3 + 0.05, a3 + 0.1)):
            n = 200
            anyp = np.zeros(reps, dtype=bool)
            for R in risks:
                losses = (rng.random((reps, n)) < R).astype(float)
                anyp |= betting_pass(losses, a3, kappa, thr, "agrapa")
            p = anyp.mean()
            full_rows.append({"alpha3": a3, "risks": list(risks), "n_cal": n,
                              "bad_selected_rate": p, "se": math.sqrt(p * (1 - p) / reps),
                              "limit": delta})

    # потужність: ризик удвічі нижчий за alpha3
    power_rows = []
    for a3 in (0.1, 0.2, 0.3):
        for n in (50, 100, 300):
            losses = (rng.random((20000, n)) < a3 / 2).astype(float)
            power_rows.append({"alpha3": a3, "R": a3 / 2, "n_cal": n,
                               "pass_rate": betting_pass(losses, a3, kappa, thr, "agrapa").mean()})

    # скільки перевірних текстів потрібно, щоб тест пройшов з імовірністю >= 0,8 за R = alpha3/2
    # (передбачувана ставка; рахуємо, чи пройшов тест до n-го тексту включно)
    power_curve = []
    n_grid = (70, 100, 150, 200, 300, 400, 600, 800)
    for a3 in (0.0625, 0.1, 0.2):
        losses = (rng.random((20000, max(n_grid)), dtype=np.float64) < a3 / 2).astype(float)
        for n in n_grid:
            pr = betting_pass(losses[:, :n], a3, kappa, thr, "agrapa").mean()
            power_curve.append({"alpha3": a3, "R": a3 / 2, "n_cal": n, "pass_rate": pr})

    # без ізоляції: перевірні тексти утворюють кластери, що спільно бачать той самий
    # хибний чи правильний фрагмент через пошук; маргінальний ризик кожного тексту = alpha3
    iso_rows = []
    for a3 in (0.1, 0.2):
        for cluster in (1, 5, 10, 20):
            n = 200
            n_cl = math.ceil(n / cluster)
            base = (rng.random((reps, n_cl)) < a3).astype(float)
            losses = np.repeat(base, cluster, axis=1)[:, :n]
            # перевірні тексти беруть у випадковому порядку (дод. А.1)
            perm = rng.permuted(np.tile(np.arange(n), (reps, 1)), axis=1)
            losses = np.take_along_axis(losses, perm, axis=1)
            p = betting_pass(losses, a3, kappa, thr, "agrapa").mean()
            iso_rows.append({"alpha3": a3, "cluster_size": cluster, "n_cal": n,
                             "pass_rate": p, "se": math.sqrt(p * (1 - p) / reps),
                             "limit": delta / J})

    ok = (all(v["formula"] == v["direct"] for v in nmin.values())
          and [nmin[k]["formula"] for k in ("0.1", "0.2", "0.3", "0.0625")] == [43, 20, 13, 70]
          and worst_null <= delta / J
          and all(r["bad_selected_rate"] - 3 * r["se"] <= delta for r in full_rows))
    RESULTS["T1b"] = {"J": J, "delta": delta, "kappa": kappa, "n_min": nmin,
                      "null": null_rows, "null_worst_minus_3se": worst_null,
                      "full_procedure": full_rows, "power": power_rows, "power_curve": power_curve,
                      "isolation_violation": iso_rows, "ok": ok}
    log(f"T1b: n_min = {nmin}")
    log(f"T1b: найбільша частка хибних проходжень (мінус 3 SE) = {worst_null:.4f} при межі {delta / J:.4f}")
    for r in power_curve:
        log(f"T1b потужність: alpha3={r['alpha3']} R={r['R']:.4f} n_cal={r['n_cal']} проходжень={r['pass_rate']:.3f}")
    for r in iso_rows:
        log(f"T1b ізоляція: alpha3={r['alpha3']} кластер={r['cluster_size']} "
            f"проходжень={r['pass_rate']:.4f} (межа {r['limit']:.4f})")


# ---------------------------------------------------------------- T2
def simulate_stream(rng, n_new, q, u, a3, m_max, n_pop, zipf_s, n_tail, beta_pop,
                    k_max, mix_correct, zeta):
    """Один потік нових текстів. Повертає (T3, Tf, Tc, N3c, FE3)."""
    w = 1.0 / np.arange(1, n_pop + 1) ** zipf_s
    w /= w.sum()
    correct_acc = set()      # вразливості з прийнятим правильним твердженням з A3
    correct_any = set()      # вразливості з будь-яким правильним кандидатом (ідеальна стадія S3)
    false_acc = set()
    t3 = tf = 0
    for _ in range(n_new):
        if rng.random() < zeta:   # відхилений правильний кандидат (впливає лише на s1*)
            v = ("p", int(rng.choice(n_pop, p=w))) if rng.random() < 0.5 else ("t", int(rng.integers(n_tail)))
            correct_any.add(v)
        if rng.random() >= q:
            continue
        t3 += 1
        if rng.random() < u * a3:
            tf += 1
            m = int(rng.integers(1, m_max + 1))
            chosen = set()
            while len(chosen) < m:
                if rng.random() < beta_pop:
                    chosen.add(("p", int(rng.choice(n_pop, p=w))))
                else:
                    chosen.add(("t", int(rng.integers(n_tail))))
            false_acc |= chosen
            if rng.random() < mix_correct:          # у тексті з хибними є й правильні
                for _ in range(int(rng.integers(1, 3))):
                    v = ("p", int(rng.choice(n_pop, p=w)))
                    if v not in chosen:
                        correct_acc.add(v)
        else:
            for _ in range(int(rng.integers(1, k_max + 1))):
                correct_acc.add(("p", int(rng.choice(n_pop, p=w))))
    correct_any |= correct_acc
    fe3 = len(false_acc - correct_any)
    return t3, tf, t3 - tf, len(correct_acc), fe3


def t2():
    rng = np.random.default_rng(33)
    pyr = random.Random(33)
    configs = []
    for _ in range(36):
        configs.append({
            "n_new": pyr.choice([1, 5, 20, 60]),
            "q": pyr.choice([0.2, 0.5, 1.0]),
            "u": pyr.choice([0.5, 1.0, 1.0]),
            "a3": pyr.choice([0.05, 0.1, 0.2, 0.3, 0.5]),
            "m_max": pyr.choice([1, 2, 3, 5]),
            "n_pop": pyr.choice([5, 30, 300]),
            "zipf_s": pyr.choice([0.0, 1.0, 1.5]),
            "n_tail": pyr.choice([10, 1000, 10 ** 6]),
            "beta_pop": pyr.choice([0.0, 0.3, 0.8]),
            "k_max": pyr.choice([1, 2, 4]),
            "mix_correct": pyr.choice([0.0, 0.3]),
            "zeta": pyr.choice([0.0, 0.1]),
        })
    rows = []
    for cfg in configs:
        # короткі потоки дешеві: більше повторів, щоб точкова оцінка відношення була стійкою
        reps = 40000 if cfg["n_new"] <= 5 else 6000
        vals = np.array([simulate_stream(rng, **cfg) for _ in range(reps)], dtype=float)
        t3, tf, tc, n3c, fe3 = vals.T
        a3, m = cfg["a3"], cfg["m_max"]
        # (1) E[Tf] <= a3 E[T3]  <=>  E[a3*T3 - Tf] >= 0
        d1 = a3 * t3 - tf
        # (2) E[FE3]/E[N3c] <= M*xi*a3/(1-a3)  <=>  E[M*a3/(1-a3)*Tc - FE3] >= 0
        d2 = m * a3 / (1 - a3) * tc - fe3
        en3c = n3c.mean()
        lhs = fe3.mean() / en3c if en3c > 0 else float("nan")
        xi = tc.mean() / en3c if en3c > 0 else float("nan")
        rhs = m * xi * a3 / (1 - a3) if en3c > 0 else float("nan")
        rows.append({**cfg, "reps": reps,
                     "E_T3": t3.mean(), "E_Tf": tf.mean(), "E_Tc": tc.mean(),
                     "E_N3c": en3c, "E_FE3": fe3.mean(), "xi_bar": xi,
                     "lhs": lhs, "rhs": rhs, "ratio": lhs / rhs if rhs and rhs > 0 else float("nan"),
                     "z1": d1.mean() / (d1.std(ddof=1) / math.sqrt(reps) + 1e-12),
                     "z2": d2.mean() / (d2.std(ddof=1) / math.sqrt(reps) + 1e-12)})
    # Двоетапне правило: конфігурацію з z < -3 повторюємо з незалежним зерном і 4x повторів;
    # порушенням вважаємо лише z < -3 в обох прогонах. Причина: у точних випадках (u = 1)
    # сподівання різниці дорівнює нулю, тож z ~ N(0,1), і серед 36 тестів z < -3 трапляється випадково.
    rng_rep = np.random.default_rng(2026)
    for r in rows:
        r["replication"] = None
        for key, dfun in (("z1", lambda t3, tf, tc, fe3, a3, m: a3 * t3 - tf),
                          ("z2", lambda t3, tf, tc, fe3, a3, m: m * a3 / (1 - a3) * tc - fe3)):
            if r[key] < -3:
                cfg = {k: r[k] for k in configs[0].keys()}
                reps2 = 4 * r["reps"]
                vals2 = np.array([simulate_stream(rng_rep, **cfg) for _ in range(reps2)], dtype=float)
                t3b, tfb, tcb, n3cb, fe3b = vals2.T
                db = dfun(t3b, tfb, tcb, fe3b, cfg["a3"], cfg["m_max"])
                zb = db.mean() / (db.std(ddof=1) / math.sqrt(reps2) + 1e-12)
                r["replication"] = {"stat": key, "reps": reps2, "z": zb}
    def confirmed(key):
        return [r for r in rows if r[key] < -3 and r["replication"] is not None
                and r["replication"]["stat"] == key and r["replication"]["z"] < -3]
    min_z1 = min(r["z1"] for r in rows)
    min_z2 = min(r["z2"] for r in rows)
    tight = [r["z1"] for r in rows if r["u"] == 1.0]
    tight_mean = float(np.mean(tight))
    tight_sd = float(np.std(tight, ddof=1))
    max_ratio = max(r["ratio"] for r in rows if not math.isnan(r["ratio"]))

    # дод. А.2: точні сподівання і Монте-Карло
    a2_rows = []
    for a3 in (0.1, 0.3):
        for m in (1, 3):
            for n in (1, 5, 20):
                for q in (0.3, 1.0):
                    for L in (max(m, 10), 100, 10 ** 4, 10 ** 6):
                        # expm1/log1p: без втрати точності за великих L
                        e_fe = -L * math.expm1(n * math.log1p(-q * a3 * m / L))
                        e_n3c = -math.expm1(n * math.log1p(-q * (1 - a3)))
                        e_tc = n * q * (1 - a3)
                        xi = e_tc / e_n3c
                        rhs = m * xi * a3 / (1 - a3)
                        lhs = e_fe / e_n3c
                        lower = rhs - (n * m) ** 2 / (2 * L * e_n3c)
                        a2_rows.append({"alpha3": a3, "M_max": m, "n_new": n, "q": q, "L": L,
                                        "lhs": lhs, "rhs": rhs, "lower_A2": lower,
                                        "lhs_over_rhs": lhs / rhs,
                                        "order_ok": lower <= lhs * (1 + 1e-12) and lhs <= rhs * (1 + 1e-12)})
    # Монте-Карло для кількох рядків як контроль точних формул
    mc_rows = []
    for (a3, m, n, q, L) in ((0.3, 3, 5, 0.3, 100), (0.1, 1, 20, 1.0, 10 ** 4), (0.3, 3, 1, 1.0, 10)):
        reps_a2 = 100000
        fe = np.zeros(reps_a2)
        n3c = np.zeros(reps_a2)
        for r in range(reps_a2):
            mentioned = set()
            tcn = 0
            for _ in range(n):
                x = rng.random()
                if x >= q:
                    continue
                if x < q * a3:
                    mentioned.update(rng.choice(L, size=m, replace=False).tolist())
                else:
                    tcn += 1
            fe[r] = len(mentioned)
            n3c[r] = 1.0 if tcn > 0 else 0.0
        exact_fe = L * (1 - (1 - q * a3 * m / L) ** n)
        exact_n3c = 1 - (1 - q * (1 - a3)) ** n
        mc_rows.append({"alpha3": a3, "M_max": m, "n_new": n, "q": q, "L": L,
                        "mc_E_FE3": fe.mean(), "exact_E_FE3": exact_fe,
                        "mc_E_N3c": n3c.mean(), "exact_E_N3c": exact_n3c})
    eq_n1 = [r for r in a2_rows if r["n_new"] == 1]
    max_dev_n1 = max(abs(r["lhs_over_rhs"] - 1) for r in eq_n1)
    big_l = [r for r in a2_rows if r["L"] == 10 ** 6]
    min_ratio_big_l = min(r["lhs_over_rhs"] for r in big_l)
    ok = (not confirmed("z1") and not confirmed("z2") and all(r["order_ok"] for r in a2_rows)
          and max_dev_n1 < 1e-9 and min_ratio_big_l > 0.999)
    RESULTS["T2"] = {"reps": "40000 за n_new<=5, інакше 6000", "configs": rows, "min_z_first": min_z1,
                     "min_z_second": min_z2, "max_ratio_lhs_rhs": max_ratio,
                     "tight_configs_z1_mean": tight_mean, "tight_configs_z1_sd": tight_sd,
                     "confirmed_violations": len(confirmed("z1")) + len(confirmed("z2")),
                     "A2_exact": a2_rows, "A2_mc_check": mc_rows,
                     "A2_n1_max_abs_dev": max_dev_n1, "A2_L1e6_min_ratio": min_ratio_big_l,
                     "ok": ok}
    log(f"T2: {len(rows)} конфігурацій (6000-40000 потоків кожна); найменші z: {min_z1:.2f} і {min_z2:.2f}; "
        f"найбільше лів./прав. = {max_ratio:.3f}")
    log(f"T2: у {len(tight)} точних конфігураціях z першої нерівності: середнє {tight_mean:.2f}, ст. відх. {tight_sd:.2f}")
    for r in rows:
        if r["replication"]:
            log(f"T2 повтор: {r['replication']['stat']} = {r[r['replication']['stat']]:.2f} -> "
                f"{r['replication']['z']:.2f} ({r['replication']['reps']} потоків, нове зерно)")
    log(f"T2: підтверджених порушень: {len(confirmed('z1')) + len(confirmed('z2'))}")
    log(f"T2 А.2: за n_new=1 відхилення від рівності {max_dev_n1:.1e}; "
        f"за L=1e6 найменше лів./прав. = {min_ratio_big_l:.6f}")
    for r in mc_rows:
        log(f"T2 А.2 МК: E[FE3] {r['mc_E_FE3']:.4f} vs {r['exact_E_FE3']:.4f}; "
            f"E[N3c] {r['mc_E_N3c']:.4f} vs {r['exact_E_N3c']:.4f}")


# ---------------------------------------------------------------- T3
def t3():
    rng = np.random.default_rng(44)
    reps = 400000
    rows = []
    viol_3a = 0
    for ng in (1, 2, 3, 5, 10):
        for p in (0.01, 0.05, 0.2):
            for c in (0.0, 0.1, 0.5, 1.0):
                for eta in (0.0, 0.2, 0.5, 1.0):
                    for model in ("mixture", "hetero"):
                        if model == "mixture":
                            # з імовірністю c усі групи помиляються разом (Bernoulli(p)),
                            # інакше незалежно: Pr(Eg)=p, Pr(Eg & Eh) = p^2 + c p(1-p) (рівність у H2)
                            common = rng.random(reps) < c
                            shock = rng.random(reps) < p
                            indep = rng.random((reps, ng)) < p
                            e = np.where(common[:, None], shock[:, None], indep)
                        else:
                            # різні p_g <= p, незалежні помилки: Pr(Eg & Eh) = p_g p_h <= p^2
                            pg = rng.uniform(0, p, size=ng)
                            e = rng.random((reps, ng)) < pg[None, :]
                        twin = (rng.random((reps, ng)) < eta) & e     # D_g лише за E_g
                        # γ: справжні групи можуть бути помилково злиті в одну призначену групу
                        merge = rng.random(reps) < 0.2
                        n_err = e.sum(axis=1)
                        gamma_groups = np.where(merge & (n_err >= 2), 1, n_err) + twin.sum(axis=1)
                        fe1 = n_err >= 1
                        fe2 = gamma_groups >= 2
                        viol_3a += int((fe2 & ~fe1).sum())
                        b1 = ng * p
                        b2 = math.comb(ng, 2) * (p * p + c * p * (1 - p)) + ng * p * eta
                        p1, p2 = fe1.mean(), fe2.mean()
                        se1 = math.sqrt(max(p1 * (1 - p1), 1e-12) / reps)
                        se2 = math.sqrt(max(p2 * (1 - p2), 1e-12) / reps)
                        rows.append({"n_g": ng, "p": p, "c": c, "eta": eta, "model": model,
                                     "Pr_FE1": p1, "B1": b1, "Pr_FE2": p2, "B2": b2,
                                     "z1": (b1 - p1) / se1, "z2": (b2 - p2) / se2})
    min_z1 = min(r["z1"] for r in rows)
    min_z2 = min(r["z2"] for r in rows)

    # r~ і табл. 4
    def rt(ng, p, c, eta):
        return (ng - 1) / 2 * (p + c * (1 - p)) + eta

    table4 = {}
    for ng in (1, 2, 5):
        for c, eta in ((0, 0), (0, 0.2), (0.1, 0), (0.1, 0.2), (0.5, 0), (0.5, 0.2)):
            b1 = ng * 0.01
            b2 = math.comb(ng, 2) * (0.01 ** 2 + c * 0.01 * 0.99) + ng * 0.01 * eta
            table4[f"ng={ng},c={c},eta={eta}"] = {
                "r_formula": rt(ng, 0.01, c, eta), "B2_over_B1": b2 / b1,
                "min1": min(1.0, rt(ng, 0.01, c, eta))}
    paper_t4 = {"ng=1": [0, 0.20, 0, 0.20, 0, 0.20], "ng=2": [0.005, 0.205, 0.055, 0.255, 0.253, 0.453],
                "ng=5": [0.020, 0.220, 0.218, 0.418, 1, 1]}
    t4_ok = True
    for ng in (1, 2, 5):
        vals = [table4[f"ng={ng},c={c},eta={eta}"]["min1"]
                for c, eta in ((0, 0), (0, 0.2), (0.1, 0), (0.1, 0.2), (0.5, 0), (0.5, 0.2))]
        for got, paper in zip(vals, paper_t4[f"ng={ng}"]):
            if abs(got - paper) > 0.0006:
                t4_ok = False
    formula_ok = all(abs(v["r_formula"] - v["B2_over_B1"]) < 1e-12 for v in table4.values())

    # приклад 2: n_g = 2, p = 0,01, c = 0, eta = 0; помилки лише разом з імовірністю 1e-4
    pe, pboth = 1e-4, 1e-4
    ex2 = {"H1": pe <= 0.01, "H2": pboth <= 0.01 ** 2 + 0, "Pr_FE1": pe, "Pr_FE2": pboth,
           "actual_ratio": pboth / pe, "r_tilde": rt(2, 0.01, 0, 0)}

    ok = min_z1 > -3 and min_z2 > -3 and viol_3a == 0 and t4_ok and formula_ok
    RESULTS["T3"] = {"reps": reps, "rows": rows, "min_z_B1": min_z1, "min_z_B2": min_z2,
                     "violations_3a": viol_3a, "table4": table4, "table4_matches_paper": t4_ok,
                     "r_formula_ok": formula_ok, "example2": ex2, "ok": ok}
    log(f"T3: {len(rows)} випадків по {reps}; найменші z до меж: {min_z1:.1f} і {min_z2:.1f}; "
        f"порушень 3(а): {viol_3a}; табл. 4 збігається: {t4_ok}")


# ---------------------------------------------------------------- стадія і властивості
def stage(claims, v, t, m):
    """claims: список словників з полями tau, rho, gamma, w, r, vul, mu, pi."""
    g2, g3 = set(), set()
    for a in claims:
        if a["tau"] < t and a["rho"] == 1 and a["vul"] == v and a["mu"] == "actual" and a["pi"] == "+":
            if a["r"] == "R3":
                g3.add(a["gamma"])
            elif a["r"] == "R2":
                g2.add(a["gamma"])
    s = 1
    if g2:
        s = 2
    if len(g3) >= m:
        s = 3
    return s


def support(claims, v, t, rtype):
    best = {}
    for a in claims:
        if a["tau"] < t and a["rho"] == 1 and a["vul"] == v and a["mu"] == "actual" \
                and a["pi"] == "+" and a["r"] == rtype:
            best[a["gamma"]] = max(best.get(a["gamma"], 0.0), a["w"])
    return sum(best.values())


def rand_claim(pyr, n_v, t_max, n_groups):
    return {"tau": pyr.randint(0, t_max), "rho": pyr.choice([0, 1, 1]),
            "gamma": pyr.randrange(n_groups), "w": round(pyr.random(), 3),
            "r": pyr.choice(["R2", "R3", "R3", "other"]), "vul": pyr.randrange(n_v),
            "mu": pyr.choice(["actual", "actual", "possible", "planned"]),
            "pi": pyr.choice(["+", "+", "-"]), "y": pyr.choice([0, 1])}


def props_and_t4():
    pyr = random.Random(55)
    fails = {"P1": 0, "P2": 0, "P3": 0, "P4": 0, "L1": 0, "T4a": 0}
    n_cases = 3000
    for _ in range(n_cases):
        n_v, t_max, n_groups = pyr.randint(1, 4), pyr.randint(3, 12), pyr.randint(1, 5)
        claims = [rand_claim(pyr, n_v, t_max, n_groups) for _ in range(pyr.randint(0, 25))]
        ts = list(range(0, t_max + 2))
        for v in range(n_v):
            for m in (1, 2, 3):
                # P1: зміна майбутнього (tau >= t) не змінює стадію і підтримку в t
                t = pyr.choice(ts)
                fut = [dict(a) for a in claims]
                for a in fut:
                    if a["tau"] >= t:
                        a.update(rand_claim(pyr, n_v, t_max, n_groups))
                        a["tau"] = max(a["tau"], t)
                fut += [dict(rand_claim(pyr, n_v, t_max, n_groups), tau=t + pyr.randint(0, 3))]
                if stage(fut, v, t, m) != stage(claims, v, t, m) or \
                        abs(support(fut, v, t, "R3") - support(claims, v, t, "R3")) > 1e-12:
                    fails["P1"] += 1
                # P2: монотонність за t
                vals = [stage(claims, v, tt, m) for tt in ts]
                sup = [support(claims, v, tt, "R3") for tt in ts]
                if any(vals[i] > vals[i + 1] for i in range(len(vals) - 1)) or \
                        any(sup[i] > sup[i + 1] + 1e-12 for i in range(len(sup) - 1)):
                    fails["P2"] += 1
                # P3: копія (ті самі r, vul, mu, pi, gamma, w' <= w) нічого не змінює
                if claims:
                    a = pyr.choice(claims)
                    cp = dict(a, w=a["w"] * pyr.random(), tau=a["tau"] + pyr.randint(0, 2))
                    # копія входить до X разом з оригіналом: порівнюємо на моменті, коли обидва в X
                    tt = max(a["tau"], cp["tau"]) + 1
                    if a["rho"] == 1 and cp["rho"] == 1:
                        if stage(claims + [cp], v, tt, m) != stage(claims, v, tt, m) or \
                                abs(support(claims + [cp], v, tt, "R3") - support(claims, v, tt, "R3")) > 1e-12:
                            fails["P3"] += 1
                # P4: твердження з mu != actual, або pi = '-', або r не стадійний
                b = []
                for _ in range(pyr.randint(1, 5)):
                    x = rand_claim(pyr, n_v, t_max, n_groups)
                    kind = pyr.choice(["mu", "pi", "r"])
                    if kind == "mu":
                        x["mu"] = pyr.choice(["possible", "planned", "conditional", "recommended", "unknown"])
                    elif kind == "pi":
                        x["pi"] = "-"
                    else:
                        x["r"] = "other"
                    b.append(x)
                t = pyr.choice(ts)
                if stage(claims + b, v, t, m) != stage(claims, v, t, m) or \
                        abs(support(claims + b, v, t, "R3") - support(claims, v, t, "R3")) > 1e-12:
                    fails["P4"] += 1
                # лема 1: хибне підвищення => хибні прийняті R3 щонайменше з m груп
                t = pyr.choice(ts)
                ideal = [dict(a, rho=1) for a in claims if a["y"] == 1]   # K*: усі правильні кандидати
                if stage(claims, v, t, m) == 3 and stage(ideal, v, t, 1) < 3:
                    groups = {a["gamma"] for a in claims if a["tau"] < t and a["rho"] == 1 and a["vul"] == v
                              and a["mu"] == "actual" and a["pi"] == "+" and a["r"] == "R3" and a["y"] == 0}
                    if len(groups) < m:
                        fails["L1"] += 1
            # T4(а): s1 = 3 <=> t(1) < t;  s2 = 3 <=> t(2) < t
            tg = {}
            for a in claims:
                if a["rho"] == 1 and a["vul"] == v and a["mu"] == "actual" and a["pi"] == "+" and a["r"] == "R3":
                    tg[a["gamma"]] = min(tg.get(a["gamma"], math.inf), a["tau"])
            srt = sorted(tg.values()) + [math.inf, math.inf]
            for t in ts:
                if (stage(claims, v, t, 1) == 3) != (srt[0] < t) or (stage(claims, v, t, 2) == 3) != (srt[1] < t):
                    fails["T4a"] += 1
    # T4(б): вичерпно на цілих числах, точні дроби
    t4b_bad = 0
    t4b_n = 0
    for tp1 in range(1, 21):
        for fp1 in range(1, 21):
            for tp2 in range(0, tp1 + 1):
                for fp2 in range(0, fp1 + 1):
                    if tp2 + fp2 == 0:
                        continue
                    t4b_n += 1
                    better = Fraction(tp2, tp2 + fp2) > Fraction(tp1, tp1 + fp1)
                    r = Fraction(fp2, fp1)
                    ell = 1 - Fraction(tp2, tp1)
                    if better != (r < 1 - ell):
                        t4b_bad += 1
    RESULTS["P_T4"] = {"random_cases": n_cases, "failures": fails,
                       "T4b_cases": t4b_n, "T4b_failures": t4b_bad,
                       "ok": all(v == 0 for v in fails.values()) and t4b_bad == 0}
    log(f"Властивості й теорема 4: порушень {fails}; T4(б): {t4b_bad} з {t4b_n}")


# ---------------------------------------------------------------- табл. 3 і числа п. 5.3
def numbers():
    t3 = {}
    for a3 in (0.05, 0.1, 0.2, 0.3):
        t3[str(a3)] = [round(xi * a3 / (1 - a3), 3) for xi in (1, 3, 10)]
    paper = {"0.05": [0.053, 0.158, 0.526], "0.1": [0.111, 0.333, 1.111],
             "0.2": [0.250, 0.750, 2.500], "0.3": [0.429, 1.286, 4.286]}
    a_req = 0.2 / (1 * 3 + 0.2)
    RESULTS["numbers"] = {"table3": t3, "table3_matches_paper": t3 == paper,
                          "alpha3_for_beta_0.2_xi_3": a_req,
                          "ok": t3 == paper and abs(a_req - 0.0625) < 1e-12}
    log(f"Табл. 3 збігається: {t3 == paper}; alpha3 для beta=0,2, xi=3: {a_req}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results.json")
    args = ap.parse_args()
    t0 = time.time()
    t1a()
    t1b()
    t2()
    t3()
    props_and_t4()
    numbers()
    RESULTS["all_ok"] = all(v.get("ok", True) for v in RESULTS.values() if isinstance(v, dict))
    RESULTS["seconds"] = round(time.time() - t0, 1)
    import scipy
    RESULTS["versions"] = {"python": sys.version.split()[0], "numpy": np.__version__,
                           "scipy": scipy.__version__}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1, default=float)
    log(f"Усе гаразд: {RESULTS['all_ok']}")


if __name__ == "__main__":
    main()
