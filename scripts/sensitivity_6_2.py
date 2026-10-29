"""Numerical scenarios of Section 5.4 (scale of the bounds of Theorem 3).

All numbers follow from Theorem 3(b) and the exact binomial formula for zero errors.
The population size is the scale of the test period of stage-early-warning v1.2 (Section 1):
76 754 candidates, of which 40 had structured S3, so 76 714 vulnerabilities are below S3
(recount: scripts/test_period.py data/test_period.csv.gz).
The values of p, c and eta are scenario assumptions, not estimates.

Usage: python3 scripts/sensitivity_6_2.py
Only the Python standard library is needed.
"""
import math

N = 76_754 - 40          # vulnerabilities with ideal base stage below S3


def b1(n_g, p):
    """Theorem 3(b): bound for the base rule, per vulnerability."""
    return n_g * p


def b2(n_g, p, c, eta):
    """Theorem 3(b): bound for the two-group rule, per vulnerability."""
    return math.comb(n_g, 2) * (p * p + c * p * (1 - p)) + n_g * p * eta


def zero_error_upper(n, level=0.95):
    """One-sided upper confidence bound for a Bernoulli probability after 0 errors in n trials."""
    return 1 - (1 - level) ** (1 / n)


def groups_needed(p_target, level=0.95):
    """Smallest n with zero_error_upper(n) <= p_target."""
    return math.ceil(math.log(1 - level) / math.log(1 - p_target))


print(f"population below S3: {N}")
print("one group, p = 1e-3")
print(f"  base rule, bound on expected false S3: {N * b1(1, 1e-3):.1f}")
print(f"  p needed for bound <= 10: {10 / N:.3e}")
print("small frequencies (zero errors, 95% one-sided)")
print(f"  upper bound after 2995 groups: {zero_error_upper(2995):.7f}")
print(f"  groups needed for 0.00013: {groups_needed(0.00013)}")
print("two-group rule with one group, p = 1e-3, eta = 0.1")
print(f"  bound on expected false S3: {N * b2(1, 1e-3, 0, 0.1):.2f}")
print("three groups, p = 1e-3")
print(f"  base rule: {N * b1(3, 1e-3):.1f}")
for c, eta in ((0, 0), (0.1, 0), (0, 0.1)):
    print(f"  two-group rule, c = {c}, eta = {eta}: {N * b2(3, 1e-3, c, eta):.2f}")
