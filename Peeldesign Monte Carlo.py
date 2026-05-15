import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


n_sims = 10000

pallet_size = 32
uses = 120
hourly_rate = 40
peel_coating_time = 0.25 + 0.25 #prep + coating for a batch of 4
years= 10

class Case:
    """
    Cost model for peeldesign case

    Attributes:
        purchase (float): Initial purchase cost
        storage (float): monthly storage cost, is divided by pallet size
        storage_months(int): standard 12
        coating_cost = cost of coating application (external)
        peelcoating_cost = cost per unit of peelcoating material
        transport_cost (float): cost for transport, is divided by pallet size


    """

    def __init__(self, name,
                 purchase=190,
                 storage = 5,
                 storage_months=12,
                 coating_cost = 10,
                 peelcoating_price=2.3375,
                 coating_internal=False,
                 transport_cost = 85,
                 transport_amount=0,
                 decoating_time = 7,
                 rental_cost =0,
                 yearly_uses=12,
                 max_uses=120,
                 powder=False):

        self.name = name

        self.purchase = purchase

        self.storage = storage/pallet_size
        self.storage_months = storage_months
        self.transport_cost = transport_cost/pallet_size
        self.transport_amount = transport_amount
        self.decoating_time = decoating_time
        self.rental_cost = rental_cost

        self.coating_cost = coating_cost
        self.peelcoating_price=peelcoating_price
        self.coating_internal=coating_internal
        self.powder=powder

        self.yearly_uses = yearly_uses
        self.max_uses = max_uses

    def calc_cost(self,
        storage = None,
        transport_cost = None,
        coating_cost = None,
        decoating_time = None,
        rental_cost = None,
        max_uses = None,
        peelcoating_price = None,
                  ):

        # Use simulated values if provided, otherwise fall back to object defaults
        storage = self.storage if storage is None else storage / pallet_size
        transport_cost = self.transport_cost if transport_cost is None else transport_cost / pallet_size
        coating_cost = self.coating_cost if coating_cost is None else coating_cost
        decoating_time = self.decoating_time if decoating_time is None else decoating_time
        rental_cost = self.rental_cost if rental_cost is None else rental_cost
        max_uses = self.max_uses if max_uses is None else max_uses
        peelcoating_price = self.peelcoating_price if peelcoating_price is None else peelcoating_price


        price = 0


        if self.powder:
            purchase = self.purchase  + coating_cost + storage + transport_cost
            purchase = purchase * np.ceil(uses / max_uses)
        else:
            purchase = self.purchase * np.ceil(uses / max_uses)

        storage = self.storage_months*storage*years

        if self.coating_internal:
            coating_cost_total = self.yearly_uses * ((hourly_rate*peel_coating_time + 4*peelcoating_price)/4)
        elif self.powder:
            coating_cost_total = 0
        else:
            coating_cost_total = coating_cost*self.yearly_uses
        coating_cost_total = coating_cost_total*years

        transport_total = transport_cost*self.transport_amount*self.yearly_uses*years

        rental_total = rental_cost*self.yearly_uses*years

        decoating_total = (decoating_time/60)*hourly_rate*self.yearly_uses*years

        price = (purchase
                + storage
                + coating_cost_total
                + transport_total
                + rental_total
                + decoating_total
                 )
        #print(purchase, storage, coating_cost_total, transport_total, rental_total, decoating_total)


        return price


a = Case("A", coating_internal=True, transport_amount=2)
b = Case("B", coating_cost=15, transport_amount=3)
c = Case("C", rental_cost=19, coating_internal=True, transport_amount=2)
d = Case("D", yearly_uses=6, max_uses=6, powder=True, transport_amount=2, decoating_time=0, coating_cost=9)
e = Case("E", coating_cost=0, transport_amount=2, decoating_time=0)


print(f'{d.calc_cost()}')


cases = [a, b, c, d, e]
"""
def sample_pert(minimum, mode, maximum, lamb=4):
    alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
    beta = 1 + lamb * (maximum - mode) / (maximum - minimum)
    return minimum + np.random.beta(alpha, beta) * (maximum - minimum)

def sample_peelcoating():
    if np.random.rand() < 0.95:
        return np.random.triangular(1.5, 2.33, 2.8)
    else:
        return np.random.triangular(1, 3, 15)

def sample_uses():
    if np.random.rand() < 0.95:
        return 120
    else:
        return np.random.triangular(6, 60, 120)

def sample_inputs():

    #Sample one scenario of uncertain inputs.
    #Adjust these distributions to match your business assumptions.

    return {
        "storage": np.random.uniform(2.5, 10),                 # around 5
        "transport_cost": np.random.uniform(60, 120),       # around 85
        "coating_cost": sample_pert(5, 9, 20),        # low to high
        "decoating_time": np.random.triangular(1, 7,14),   # centered on 7
        "max_uses": sample_uses(),            # example uncertainty
        "peelcoating_price": sample_peelcoating()   # example range
    }


results = []

for sim in range(n_sims):
    sampled = sample_inputs()

    row = {
        "sim": sim + 1,
        "storage": sampled["storage"],
        "transport_cost": sampled["transport_cost"],
        "coating_cost": sampled["coating_cost"],
        "decoating_time": sampled["decoating_time"],
        "max_uses": sampled["max_uses"],
        "peelcoating_price": sampled["peelcoating_price"],
    }

    for case in cases:
        # max_uses
        if case.name == "D":
            max_uses = case.max_uses
        else:
            max_uses = sampled["max_uses"]

        # decoating_time
        if case.name in ["D", "E"]:
            decoating_time = case.decoating_time
        else:
            decoating_time = sampled["decoating_time"]

        # coating_cost
        if case.name == "E":
            coating_cost = case.coating_cost
        else:
            coating_cost = sampled["coating_cost"]

        row[case.name] = case.calc_cost(
            storage=sampled["storage"],
            transport_cost=sampled["transport_cost"],
            coating_cost=coating_cost,
            decoating_time=decoating_time,
            max_uses=max_uses,
            peelcoating_price=sampled["peelcoating_price"],
        )

    results.append(row)

df = pd.DataFrame(results)

print(df.head())
print()
print("Average cost per case:")
print(df[["A", "B", "C", "D", "E"]].mean())

winner = df[["A", "B", "C", "D", "E"]].idxmin(axis=1)
print()
print("Probability each case is cheapest:")
print(winner.value_counts(normalize=True).sort_index())

print(df[["A","B","C","D","E"]].describe())


corr = df.corr(numeric_only=True)

inputs = ["storage","transport_cost","coating_cost","decoating_time","max_uses","peelcoating_price"]
for case in ["A","B","C","D","E"]:
    print(f"\n--- {case} ---")
    print(df[inputs + [case]].corr()[case].drop(case).sort_values(ascending=False))
"""

# -----------------------
# Settings
# -----------------------

cutoff = 4373.75

max_uses_slices = [120, 96, 48, 24, 12, 6]

transport_slices = {
    "Low transport": 60,
    "Mid transport": 85,
    "High transport": 120,
}

peelcoating_values = np.linspace(1.5, 15, 80)
decoating_values = np.linspace(1, 14, 80)

# -----------------------
# Build plot
# -----------------------

cmap = plt.cm.RdYlGn_r  # reversed so green = low, red = high

norm = mcolors.Normalize(vmin=1600, vmax=cutoff)

fig, axes = plt.subplots(
    nrows=len(max_uses_slices),
    ncols=len(transport_slices),
    figsize=(15, 22),
    sharex=True,
    sharey=True,
)

# shared color scale below cutoff
vmin = 0
vmax = cutoff

for row_idx, max_uses in enumerate(max_uses_slices):
    for col_idx, (transport_label, transport_cost) in enumerate(transport_slices.items()):

        Z = np.zeros((len(decoating_values), len(peelcoating_values)))

        for i, decoating_time in enumerate(decoating_values):
            for j, peelcoating_price in enumerate(peelcoating_values):

                price = a.calc_cost(
                    peelcoating_price=peelcoating_price,
                    decoating_time=decoating_time,
                    transport_cost=transport_cost,
                    max_uses=max_uses,
                    storage=5,
                )

                # Hide values above cutoff
                if price > cutoff:
                    Z[i, j] = np.nan
                else:
                    Z[i, j] = price

        ax = axes[row_idx, col_idx]

        im = ax.imshow(
            Z,
            origin="lower",
            aspect="auto",
            extent=[
                peelcoating_values.min(),
                peelcoating_values.max(),
                decoating_values.min(),
                decoating_values.max(),
            ],
            cmap=cmap,
            norm=norm,
        )

        ax.set_title(f"{transport_label} | max uses = {max_uses}")


        x_ticks = np.linspace(peelcoating_values.min(), peelcoating_values.max(), 6)
        y_ticks = np.linspace(decoating_values.min(), decoating_values.max(), 6)

        ax.set_xticks(x_ticks)
        ax.set_yticks(y_ticks)

        ax.grid(True, which='major', color='black', linestyle='-', linewidth=0.5, alpha=0.3)

        # Optional: mark base values
        ax.axvline(2.3375, linestyle="--", linewidth=1)
        ax.axhline(7, linestyle="--", linewidth=1)

# -----------------------
# Shared colorbar
# -----------------------

fig.subplots_adjust(right=0.88, hspace=0.35, wspace=0.15)

cbar_ax = fig.add_axes([0.9, 0.15, 0.02, 0.7])
fig.colorbar(im, cax=cbar_ax, label="Total price")

fig.text(0.5, 0.04, "Peelcoating price", ha="center", fontsize=12)
fig.text(0.04, 0.5, "Decoating time (min)", va="center", rotation="vertical", fontsize=12)

fig.suptitle(
    f"Case A total price below cutoff ({cutoff})",
    fontsize=16,
    y=0.995,
)

plt.show()
