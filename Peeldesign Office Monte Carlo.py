import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
from pathlib import Path


n_sims = 10000

pallet_size = 2
uses = 120
hourly_rate = 40
years= 10
PRICE_PEELCOATING = 2.3375

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
                 #purchase=190,
                 storage = 5,
                 storage_months=12,
                 coating_cost = 14,
                 peelcoating_price=14.62,
                 peelcoating_time=20,
                 coating_internal=False,
                 transport_cost = 85,
                 transport_amount = 0,
                 decoating_time = 10,
                 max_uses=120,
                 #powder=False
                 ):

        self.name = name

        #self.purchase = purchase

        self.storage = storage/pallet_size
        self.storage_months = storage_months
        self.transport_cost = transport_cost/pallet_size
        self.transport_amount = transport_amount
        
        self.coating_cost = coating_cost
        self.peelcoating_price=peelcoating_price
        self.coating_internal=coating_internal
        self.peelcoating_time=peelcoating_time
        self.decoating_time = decoating_time


        self.max_uses = max_uses

    def calc_cost_per_loop(self,
        storage = None,
        transport_cost = None,
        coating_cost = None,
        peelcoating_time = None,
        decoating_time = None,
        peelcoating_price = None,
                  ):

        return sum(self.cost_breakdown_per_loop(
            storage=storage,
            transport_cost=transport_cost,
            coating_cost=coating_cost,
            peelcoating_time=peelcoating_time,
            decoating_time=decoating_time,
            peelcoating_price=peelcoating_price,
        ).values())

    def cost_breakdown_per_loop(self,
        storage = None,
        transport_cost = None,
        coating_cost = None,
        peelcoating_time = None,
        decoating_time = None,
        peelcoating_price = None,
                  ):

        # Use simulated values if provided, otherwise fall back to object defaults
        storage = self.storage if storage is None else storage / pallet_size
        transport_cost = self.transport_cost if transport_cost is None else transport_cost / pallet_size
        coating_cost = self.coating_cost if coating_cost is None else coating_cost
        peelcoating_time = self.peelcoating_time if peelcoating_time is None else peelcoating_time
        decoating_time = self.decoating_time if decoating_time is None else decoating_time
        peelcoating_price = self.peelcoating_price if peelcoating_price is None else peelcoating_price


        storage_total = storage * self.storage_months

        transport_total = transport_cost * self.transport_amount

        if self.coating_internal:
            coating_cost_total = peelcoating_price + (peelcoating_time / 60) * hourly_rate
        else:
            coating_cost_total = coating_cost

        decoating_total = (decoating_time / 60) * hourly_rate

        #print(storage_total, transport_total, coating_cost_total, decoating_total)

        return {
            "Storage": storage_total,
            "Transport": transport_total,
            "Coating": coating_cost_total,
            "Decoating": decoating_total,
        }

    @staticmethod
    def plot_cost_breakdown_per_loop(cases, show=True, **cost_inputs):
        cost_order = [
            "Storage",
            "Transport",
            "Coating",
            "Decoating",
        ]

        cost_breakdown = pd.DataFrame({
            case.name: case.cost_breakdown_per_loop(**cost_inputs)
            for case in cases
        }).T
        cost_breakdown = cost_breakdown[[part for part in cost_order if part in cost_breakdown.columns]]

        cost_colours = {
            "Storage": "#98beff",
            "Transport": "#3232C2",
            "Coating": "#006872",
            "Decoating": "#ffb9ca",
        }

        fig, ax = plt.subplots(figsize=(9, 5))
        bottom = np.zeros(len(cost_breakdown))

        for cost_part in cost_breakdown.columns:
            values = cost_breakdown[cost_part].to_numpy()
            ax.bar(
                cost_breakdown.index,
                values,
                bottom=bottom,
                label=cost_part,
                color=cost_colours.get(cost_part),
            )
            bottom += values

        for case_idx, total in enumerate(bottom):
            ax.text(case_idx, total, f"{total:.2f}", ha="center", va="bottom", fontsize=9)

        ax.set_xlabel("Case")
        ax.set_ylabel("Cost per loop")
        ax.set_title("Office cost per loop by case")
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.legend(title="Cost part")

        fig.tight_layout()

        if show:
            plt.show()

        return fig, ax, cost_breakdown


a = Case("A", storage=0, storage_months=0, transport_cost=0, transport_amount=0, coating_internal=True) #Recoating in shop
d = Case("B", storage_months=3, transport_amount=2, coating_internal=True) #Shopfitting as a service, coating internal
e = Case("C", storage_months=2,  transport_amount=3, coating_internal=False) #Shopfitting as a service, coating external



print(f'{a.calc_cost_per_loop()}')
print(f'{d.calc_cost_per_loop()}')
print(f'{e.calc_cost_per_loop()}')


cases = [a, d, e]
Case.plot_cost_breakdown_per_loop(cases)
case_names = [case.name for case in cases]

def sample_pert(minimum, mode, maximum, lamb=4):
    alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
    beta = 1 + lamb * (maximum - mode) / (maximum - minimum)
    return minimum + np.random.beta(alpha, beta) * (maximum - minimum)

def sample_peelcoating():
    if np.random.rand() < 0.5:
        return sample_pert(minimum=5, mode=9, maximum=14, lamb=6)
    else:
        return sample_pert(minimum=10, mode=14, maximum=18, lamb=4)

def sample_uses():
    if np.random.rand() < 0.95:
        return 120
    else:
        return np.random.triangular(6, 60, 120)

def sample_inputs():

    #Sample one scenario of uncertain inputs.
    #Adjust these distributions to match your business assumptions.

    return {
        "storage": np.random.normal(5, 2),                 # around 5
        "transport_cost": np.random.normal(85, 25),       # around 85
        "coating_cost": sample_peelcoating(),        # low to high
        "decoating_time": np.random.triangular(5, 10, 20),   # centered on 10           
        "peelcoating_price": sample_pert(11, 14, 20, lamb=4),   # example range
        "peelcoating_time": np.random.triangular(10, 20, 30),   # centered on 20
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
        "peelcoating_price": sampled["peelcoating_price"],
        "peelcoating_time": sampled["peelcoating_time"],
    }

    for case in cases:


        row[case.name] = case.calc_cost_per_loop(
            storage=sampled["storage"],
            transport_cost=sampled["transport_cost"],
            coating_cost=sampled["coating_cost"],
            decoating_time=sampled["decoating_time"],
            peelcoating_price=sampled["peelcoating_price"],
            peelcoating_time=sampled["peelcoating_time"],
        )

    results.append(row)

df = pd.DataFrame(results)

first10 = df.iloc[:10].copy()
mean_row = df.mean().to_frame().T
mean_row.index = ["Average"]
print(pd.concat([first10, mean_row]))
print()
print("Average cost per case:")
print(df[case_names].mean())

winner = df[case_names].idxmin(axis=1)
print()
print("Probability each case is cheapest:")
print(winner.value_counts(normalize=True).sort_index())

print(df[case_names].describe())


corr = df.corr(numeric_only=True)

inputs = ["storage","transport_cost","coating_cost","decoating_time","peelcoating_price", "peelcoating_time"]
for case in case_names:
    print(f"\n--- {case} ---")
    print(df[inputs + [case]].corr()[case].drop(case).sort_values(ascending=False))


def save_monte_carlo_results(df, case_names, inputs, output_dir="monte_carlo_output"):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    results_file = output_dir / "office_monte_carlo_results.csv"
    summary_file = output_dir / "office_monte_carlo_summary.json"

    df = df.copy()
    df["winner"] = df[case_names].idxmin(axis=1)
    df.to_csv(results_file, index=False)

    summary = {
        "n_sims": len(df),
        "case_names": case_names,
        "average_inputs": df[inputs].mean().to_dict(),
        "average_cost_per_case": df[case_names].mean().to_dict(),
        "probability_each_case_is_cheapest": df["winner"].value_counts(normalize=True).sort_index().to_dict(),
        "cost_descriptive_statistics": df[case_names].describe().to_dict(),
        "input_correlations_by_case": {
            case: df[inputs + [case]].corr()[case].drop(case).sort_values(ascending=False).to_dict()
            for case in case_names
        },
    }

    summary_file.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")

    return results_file, summary_file


results_file, summary_file = save_monte_carlo_results(df, case_names, inputs)
print()
print(f"Saved Monte Carlo results to: {results_file}")
print(f"Saved Monte Carlo summary to: {summary_file}")
