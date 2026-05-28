import math

import numpy as np
import matplotlib.pyplot as plt


def pert_pdf(x, minimum, mode, maximum, lamb=4):
    alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
    beta = 1 + lamb * (maximum - mode) / (maximum - minimum)

    y = np.zeros_like(x)
    inside = (minimum < x) & (x < maximum)
    scaled_x = (x[inside] - minimum) / (maximum - minimum)

    log_beta = math.lgamma(alpha) + math.lgamma(beta) - math.lgamma(alpha + beta)
    y[inside] = np.exp(
        (alpha - 1) * np.log(scaled_x)
        + (beta - 1) * np.log(1 - scaled_x)
        - log_beta
    ) / (maximum - minimum)

    return y


if_minimum = 1.5
if_mode = 2.33
if_maximum = 3.5
if_lamb = 6

elif_minimum = 2.33
elif_mode = 4.5
elif_maximum = 6
elif_lamb = 4

else_minimum = 4
else_mode = 15
else_maximum = 20
else_lamb = 4

if_weight = 0.75
elif_weight = 0.15
else_weight = 0.10
else_display_scale = 5

x = np.linspace(if_minimum, else_maximum, 2000)

if_pdf = if_weight * pert_pdf(x, if_minimum, if_mode, if_maximum, lamb=if_lamb)
elif_pdf = elif_weight * pert_pdf(x, elif_minimum, elif_mode, elif_maximum, lamb=elif_lamb)
else_pdf = else_weight * pert_pdf(x, else_minimum, else_mode, else_maximum, lamb=else_lamb)

dx = x[1] - x[0]
total_area = np.sum(if_pdf + elif_pdf + else_pdf) * dx
if_pdf = if_pdf / total_area
elif_pdf = elif_pdf / total_area
else_pdf = else_pdf / total_area
else_pdf_display = else_pdf * else_display_scale

plt.figure(figsize=(8, 4.5))

if_x = np.linspace(if_minimum, if_maximum, 500)
elif_x = np.linspace(elif_minimum, elif_maximum, 500)
else_x = np.linspace(else_minimum, else_maximum, 500)

if_y = if_weight * pert_pdf(if_x, if_minimum, if_mode, if_maximum, lamb=if_lamb) / total_area
elif_y = elif_weight * pert_pdf(elif_x, elif_minimum, elif_mode, elif_maximum, lamb=elif_lamb) / total_area
else_y = else_weight * pert_pdf(else_x, else_minimum, else_mode, else_maximum, lamb=else_lamb) / total_area

plt.plot(if_x, if_y, linewidth=2.5, color="#006872", label="Low peelcoating price")
plt.plot(elif_x, elif_y, linewidth=2.5, color="#75008D", label="Medium peelcoating price")
plt.plot(
    else_x,
    else_y * else_display_scale,
    linewidth=2.5,
    color="#ff4200",
    label=f"High peelcoating price scaled by x{else_display_scale}",
)

plt.axvline(if_minimum, color="#95a3a6", linestyle=":", linewidth=1.5, )
plt.axvline(if_mode, color="#006872", linestyle="--", linewidth=1.5, )
plt.axvline(elif_mode, color="#75008D", linestyle="--", linewidth=1.5, )
plt.axvline(else_mode, color="#ff4200", linestyle="--", linewidth=1.5, )
plt.axvline(else_maximum, color="#95a3a6", linestyle=":", linewidth=1.5, )

plt.title("Price Peelcoating (PERT distribution)")
plt.xlabel("Peelcoating price")
plt.ylabel("Probability density")
plt.xticks([1, 2.33, 3.5, 4.5, 6,  8, 10, 12.5, 15, 17.5, 20])
plt.ylim(bottom=0)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
