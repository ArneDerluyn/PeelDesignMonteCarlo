import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import json
from pathlib import Path


n_sims = 10000

pallet_size = 32
uses = 120
peelcoated_uses = 24
uncoated_uses = uses - peelcoated_uses
hourly_rate = 40
peel_coating_time = 0.25 + 0.25 #prep + coating for a batch of 4
years= 10

CASE_D_ROW_CUTOFFS = {
    6: 4507,
    12: 2987,
    24: 2227,
    48: 1923,
    96: 1771,
    120: 1619,
}

DEBUG_GRID_STANDARD_POINTS = True

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

        self.storage = storage
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
        coating_internal = None,
        decoating_time = None,
        rental_cost = None,
        max_uses = None,
        peelcoating_price = None,
                  ):

        return sum(self.cost_breakdown(
            storage=storage,
            transport_cost=transport_cost,
            coating_cost=coating_cost,
            coating_internal=coating_internal,
            decoating_time=decoating_time,
            rental_cost=rental_cost,
            max_uses=max_uses,
            peelcoating_price=peelcoating_price,
        ).values())

    @staticmethod
    def evaluate_use_split(total_uses=uses, coated_uses=peelcoated_uses):
        uncoated = total_uses - coated_uses

        return {
            "total_uses": total_uses,
            "coated_uses": coated_uses,
            "uncoated_uses": uncoated,
            "coated_weight": coated_uses / total_uses,
            "uncoated_weight": uncoated / total_uses,
        }

    def calc_cost_with_use_split(
            self,
            uncoated_case=None,
            total_uses=uses,
            coated_uses=peelcoated_uses,
            cost_inputs=None,
            uncoated_cost_inputs=None,
    ):
        cost_inputs = {} if cost_inputs is None else dict(cost_inputs)
        split = self.evaluate_use_split(total_uses=total_uses, coated_uses=coated_uses)
        coated_cost = self.calc_cost(**cost_inputs)

        if uncoated_case is None or split["uncoated_uses"] == 0:
            return coated_cost

        uncoated_cost_inputs = {} if uncoated_cost_inputs is None else dict(uncoated_cost_inputs)
        uncoated_cost = uncoated_case.calc_cost(**uncoated_cost_inputs)

        return (
            split["coated_weight"] * coated_cost
            + split["uncoated_weight"] * uncoated_cost
        )

    def cost_breakdown(self,
        storage = None,
        transport_cost = None,
        coating_cost = None,
        coating_internal = None,
        decoating_time = None,
        rental_cost = None,
        max_uses = None,
        peelcoating_price = None,
                  ):

        # Use simulated values if provided, otherwise fall back to object defaults
        storage = self.storage if storage is None else storage / pallet_size
        transport_cost = self.transport_cost if transport_cost is None else transport_cost / pallet_size
        coating_cost = self.coating_cost if coating_cost is None else coating_cost
        coating_internal = self.coating_internal if coating_internal is None else coating_internal
        decoating_time = self.decoating_time if decoating_time is None else decoating_time
        rental_cost = self.rental_cost if rental_cost is None else rental_cost
        max_uses = self.max_uses if max_uses is None else max_uses
        peelcoating_price = self.peelcoating_price if peelcoating_price is None else peelcoating_price

        replacement_count = np.ceil(uses / max_uses)

        if self.powder:
            purchase = (self.purchase + storage + transport_cost) * replacement_count
            powder_coating_total = coating_cost * replacement_count
        else:
            purchase = self.purchase * replacement_count
            powder_coating_total = 0

        storage_total = self.storage_months*storage*years/pallet_size

        if coating_internal:
            coating_cost_total = self.yearly_uses * ((hourly_rate*peel_coating_time + 4*peelcoating_price)/4)
        elif self.powder:
            coating_cost_total = 0
        else:
            coating_cost_total = coating_cost*self.yearly_uses
        coating_cost_total = coating_cost_total*years

        transport_total = transport_cost*self.transport_amount*self.yearly_uses*years
        rental_total = rental_cost*self.yearly_uses*years
        decoating_total = (decoating_time/60)*hourly_rate*self.yearly_uses*years

        return {
            "Purchase": purchase,
            "Storage": storage_total,
            "Transport": transport_total,
            "Coating": coating_cost_total,
            "Powder coating": powder_coating_total,
            "Decoating": decoating_total,
            "Rental": rental_total,
        }

    @staticmethod
    def plot_cost_build_up(cases, show=True, uncoated_case=None, blended_case_names=None, **cost_inputs):
        blended_case_names = [] if blended_case_names is None else blended_case_names
        coated_weight = peelcoated_uses / uses
        uncoated_weight = uncoated_uses / uses
        cost_order = [
            "Purchase",
            "Storage",
            "Transport",
            "Powder coating",
            "Coating",
            "Decoating",
            "Rental",
        ]

        def blended_breakdown(case):
            case_breakdown = case.cost_breakdown(**cost_inputs)

            if uncoated_case is None or case.name not in blended_case_names:
                return case_breakdown

            if case.name == "C":
                uncoated_inputs = dict(cost_inputs)
                uncoated_inputs["coating_cost"] = 0
                uncoated_inputs["coating_internal"] = False
                uncoated_inputs["decoating_time"] = 0
                uncoated_inputs["max_uses"] = case.max_uses
                uncoated_breakdown = case.cost_breakdown(**uncoated_inputs)
            else:
                uncoated_inputs = dict(cost_inputs)
                uncoated_inputs["coating_cost"] = uncoated_case.coating_cost
                uncoated_inputs["decoating_time"] = uncoated_case.decoating_time
                uncoated_inputs["max_uses"] = uncoated_case.max_uses
                uncoated_breakdown = uncoated_case.cost_breakdown(**uncoated_inputs)
            cost_parts = [
                cost_part
                for cost_part in cost_order
                if cost_part in case_breakdown or cost_part in uncoated_breakdown
            ]

            return {
                cost_part: (
                    coated_weight * case_breakdown.get(cost_part, 0)
                    + uncoated_weight * uncoated_breakdown.get(cost_part, 0)
                )
                for cost_part in cost_parts
            }

        cost_build_up = pd.DataFrame({
            case.name: blended_breakdown(case)
            for case in cases
        }).T
        cost_build_up = cost_build_up[[cost_part for cost_part in cost_order if cost_part in cost_build_up.columns]]

        colours = {
            "A": "#2d1329",
            "B": "#ff4200",
            "C": "#75008D",
            "D": "#3232C2",
            "E": "#006872",
            "F": "#95a3a6",
            "G": "#ffb9ca",
            "H": "#d6beff",
            "I": "#98beff",
            "J": "#94fff2",
            "K": "#c0022f",
        }
        cost_colours = {
            "Storage": "#98beff",
            "Coating": "#006872",
            "Powder coating": "#ff4200",
            "Purchase": "#75008D",
            "Transport": "#3232C2",
            "Decoating": "#ffb9ca",
            "Rental": "#95a3a6",
        }

        fig, ax = plt.subplots(figsize=(10, 6))
        bottom = np.zeros(len(cost_build_up))

        for cost_part in cost_build_up.columns:
            values = cost_build_up[cost_part].to_numpy()/20
            ax.bar(
                cost_build_up.index,
                values,
                bottom=bottom,
                label=cost_part,
                color=cost_colours.get(cost_part),
            )
            bottom += values

        for case_idx, total in enumerate(bottom):
            ax.text(case_idx, total, f"{total:.2f}", ha="center", va="bottom", fontsize=9)

        ax.set_xlabel("Case")
        ax.set_ylabel("Cost")
        ax.set_title("Cost per use by case")
        ax.set_ylim(0,50)
        ax.grid(True, axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.legend(title="Cost part")

        fig.tight_layout()

        if show:
            plt.show()

        return fig, ax, cost_build_up

    def plot_cost_below_cutoff(
            self,
            cutoff,
            max_uses_slices=None,
            transport_slices=None,
            peelcoating_values=None,
            decoating_values=None,
            storage=5,
            show=True,
    ):
        max_uses_slices = [120, 96, 48, 24, 12, 6] if max_uses_slices is None else max_uses_slices
        transport_slices = {
            "Low transport": 60,
            "Mid transport": 85,
            "High transport": 120,
        } if transport_slices is None else transport_slices
        peelcoating_values = np.linspace(1.5, 15, 80) if peelcoating_values is None else peelcoating_values
        decoating_values = np.linspace(1, 14, 80) if decoating_values is None else decoating_values

        cmap = plt.cm.RdYlGn_r  # reversed so green = low, red = high
        norm = mcolors.Normalize(vmin=1600, vmax=cutoff)

        fig, axes = plt.subplots(
            nrows=len(max_uses_slices),
            ncols=len(transport_slices),
            figsize=(15, 22),
            sharex=True,
            sharey=True,
        )

        axes = np.asarray(axes).reshape(len(max_uses_slices), len(transport_slices))
        im = None

        for row_idx, max_uses in enumerate(max_uses_slices):
            for col_idx, (transport_label, transport_cost) in enumerate(transport_slices.items()):

                Z = np.zeros((len(decoating_values), len(peelcoating_values)))

                for i, decoating_time in enumerate(decoating_values):
                    for j, peelcoating_price in enumerate(peelcoating_values):

                        price = self.calc_cost(
                            peelcoating_price=peelcoating_price,
                            decoating_time=decoating_time,
                            transport_cost=transport_cost,
                            max_uses=max_uses,
                            storage=storage,
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

        fig.subplots_adjust(right=0.88, hspace=0.35, wspace=0.15)

        cbar_ax = fig.add_axes([0.9, 0.15, 0.02, 0.7])
        fig.colorbar(im, cax=cbar_ax, label="Total price")

        fig.text(0.5, 0.04, "Peelcoating price", ha="center", fontsize=12)
        fig.text(0.04, 0.5, "Decoating time (min)", va="center", rotation="vertical", fontsize=12)

        fig.suptitle(
            f"Case {self.name} total price below cutoff ({cutoff})",
            fontsize=16,
            y=0.995,
        )

        if show:
            plt.show()

        return fig, axes


a = Case("A", coating_internal=True, transport_amount=2)
b = Case("B", coating_cost=15, transport_amount=3)
c = Case("C", rental_cost=19, coating_internal=True, transport_amount=2, storage=0, purchase=0)
d = Case("D", yearly_uses=6, max_uses=6, powder=True, transport_amount=2, decoating_time=0, coating_cost=9, storage=15)
e = Case("E", coating_cost=0, transport_amount=2, decoating_time=0)


cases = [a, b, c, d, e]
peelable_case_names = ["A", "B", "C", "D"]
Case.plot_cost_build_up(cases, uncoated_case=e, blended_case_names=peelable_case_names)


def sample_pert(minimum, mode, maximum, lamb=4):
    alpha = 1 + lamb * (mode - minimum) / (maximum - minimum)
    beta = 1 + lamb * (maximum - mode) / (maximum - minimum)
    return minimum + np.random.beta(alpha, beta) * (maximum - minimum)

def sample_peelcoating():
    r = np.random.rand()
    if r < 0.75:
        return sample_pert(1.5, 2.33, 3.5, lamb=6)
    elif r < 0.90:
        return sample_pert(2.33, 4.5, 6, lamb=4)
    else:
        return sample_pert(4, 15, 20)

def sample_uses():
    if np.random.rand() < 0.95:
        return 120
    else:
        return np.random.triangular(6, 60, 120)

def sample_inputs():

    #Sample one scenario of uncertain inputs.
    #Adjust these distributions to match your business assumptions.

    return {
        "storage": np.random.normal(5, 2),              # around 5
        "transport_cost": np.random.normal(85, 25),       # around 85
        "coating_cost": sample_pert(5, 9, 20),        # low to high
        "decoating_time": np.random.triangular(1, 7,14),   # centered on 7
        "max_uses": uses,
        #"max_uses": sample_uses(),            # example uncertainty
        "peelcoating_price": sample_peelcoating()   # example range
    }


def case_cost_from_sample(
        case,
        sampled,
        max_uses_override=None,
        coating_cost_override=None,
        coating_internal_override=None,
        decoating_time_override=None,
):
    max_uses = case.max_uses if case.name == "D" else sampled["max_uses"]
    max_uses = max_uses if max_uses_override is None else max_uses_override
    decoating_time = case.decoating_time if case.name in ["D", "E"] else sampled["decoating_time"]
    decoating_time = decoating_time if decoating_time_override is None else decoating_time_override
    coating_cost = case.coating_cost if case.name == "E" else sampled["coating_cost"]
    coating_cost = coating_cost if coating_cost_override is None else coating_cost_override

    return case.calc_cost(
        storage=sampled["storage"],
        transport_cost=sampled["transport_cost"],
        coating_cost=coating_cost,
        coating_internal=coating_internal_override,
        decoating_time=decoating_time,
        max_uses=max_uses,
        peelcoating_price=sampled["peelcoating_price"],
    )


def blended_case_cost(case, sampled, uncoated_case):
    if case.name not in peelable_case_names:
        return case_cost_from_sample(case, sampled)

    if case.name == "C":
        uncoated_split_case = case
        uncoated_cost_inputs = {
            "storage": sampled["storage"],
            "transport_cost": sampled["transport_cost"],
            "coating_cost": 0,
            "coating_internal": False,
            "decoating_time": 0,
            "max_uses": 120,
            "peelcoating_price": sampled["peelcoating_price"],
        }
    else:
        uncoated_split_case = uncoated_case
        uncoated_cost_inputs = {
            "storage": sampled["storage"],
            "transport_cost": sampled["transport_cost"],
            "coating_cost": uncoated_case.coating_cost,
            "decoating_time": uncoated_case.decoating_time,
            "max_uses": 120,
            "peelcoating_price": sampled["peelcoating_price"],
        }

    cost_inputs = {
        "storage": sampled["storage"],
        "transport_cost": sampled["transport_cost"],
        "coating_cost": case.coating_cost if case.name == "E" else sampled["coating_cost"],
        "decoating_time": case.decoating_time if case.name in ["D", "E"] else sampled["decoating_time"],
        "max_uses": case.max_uses if case.name == "D" else sampled["max_uses"],
        "peelcoating_price": sampled["peelcoating_price"],
    }

    return case.calc_cost_with_use_split(
        uncoated_case=uncoated_split_case,
        cost_inputs=cost_inputs,
        uncoated_cost_inputs=uncoated_cost_inputs,
    )


def plot_transport_price_cutoff(
        cases,
        cutoff,
        transport_values=None,
        peelcoating_values=None,
        coating_cost_values=None,
        storage=None,
        decoating_time=7,
        max_uses=120,
        uncoated_case=None,
        show=True,
):
    transport_values = np.linspace(40, 140, 900) if transport_values is None else transport_values
    peelcoating_values = np.linspace(1.5, 20, 900) if peelcoating_values is None else peelcoating_values
    coating_cost_values = np.linspace(5, 20, 900) if coating_cost_values is None else coating_cost_values
    uncoated_case = next(case for case in cases if case.name == "E") if uncoated_case is None else uncoated_case

    cases_by_name = {case.name: case for case in cases}
    plot_cases = [
        ("A", "peelcoating_price", peelcoating_values, "Peelcoating price"),
        ("B", "coating_cost", coating_cost_values, "Coating cost"),
        ("C", "peelcoating_price", peelcoating_values, "Peelcoating price"),
        ("D", "coating_cost", coating_cost_values, "Coating cost"),
    ]

    cmap = plt.cm.RdYlGn_r
    norm = mcolors.Normalize(vmin=100, vmax=cutoff)

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), sharex=True)
    axes = axes.ravel()
    im = None

    for ax, (case_name, y_input, y_values, y_label) in zip(axes, plot_cases):
        case = cases_by_name[case_name]
        Z = np.zeros((len(y_values), len(transport_values)))

        for y_idx, y_value in enumerate(y_values):
            for x_idx, transport_cost in enumerate(transport_values):
                sampled = {
                    "storage": storage,
                    "transport_cost": transport_cost,
                    "coating_cost": case.coating_cost,
                    "decoating_time": decoating_time,
                    "max_uses": max_uses,
                    "peelcoating_price": case.peelcoating_price,
                }
                sampled[y_input] = y_value

                price = blended_case_cost(case, sampled, uncoated_case)/20
                Z[y_idx, x_idx] = np.nan if price > cutoff else price

        im = ax.imshow(
            Z,
            origin="lower",
            aspect="auto",
            extent=[
                transport_values.min(),
                transport_values.max(),
                y_values.min(),
                y_values.max(),
            ],
            cmap=cmap,
            norm=norm,
        )

        ax.set_title(f"Case {case_name}")
        ax.set_ylabel(y_label)
        ax.grid(True, which="major", color="black", linestyle="-", linewidth=0.5, alpha=0.25)
        ax.axvline(85, linestyle="--", linewidth=1, color="black", alpha=0.7)

        if y_input == "peelcoating_price":
            ax.axhline(case.peelcoating_price, linestyle="--", linewidth=1, color="black", alpha=0.7)
        else:
            ax.axhline(case.coating_cost, linestyle="--", linewidth=1, color="black", alpha=0.7)

    axes[2].set_xlabel("Transport cost")
    axes[3].set_xlabel("Transport cost")

    fig.subplots_adjust(right=0.88, hspace=0.25, wspace=0.18)
    cbar_ax = fig.add_axes([0.9, 0.15, 0.02, 0.7])
    fig.colorbar(im, cax=cbar_ax, label="Cost per use below cutoff")
    fig.suptitle(f"Transport and coating price cutoff diagram ({cutoff})", fontsize=16, y=0.98)

    if show:
        plt.show()

    return fig, axes


def plot_case_max_use_cutoff_grid(
        cases,
        cutoff=None,
        row_cutoffs=None,
        cutoff_case_name="D",
        max_uses_values=None,
        transport_values=None,
        peelcoating_values=None,
        coating_cost_values=None,
        inactive_y_values=None,
        storage=None,
        decoating_time=7,
        uncoated_case=None,
        show=True,
):
    max_uses_values = [6, 12, 24, 48, 96, 120] if max_uses_values is None else max_uses_values
    transport_values = np.linspace(40, 140, 500) if transport_values is None else transport_values
    peelcoating_values = np.linspace(1.5, 20, 500) if peelcoating_values is None else peelcoating_values
    coating_cost_values = np.linspace(5, 20, 500) if coating_cost_values is None else coating_cost_values
    inactive_y_values = np.linspace(0, 20, 500) if inactive_y_values is None else inactive_y_values
    transport_values = np.sort(np.unique(np.append(transport_values, 85)))
    peelcoating_values = np.sort(np.unique(np.append(peelcoating_values, 2.3375)))
    coating_cost_values = np.sort(np.unique(np.append(coating_cost_values, [9, 15])))
    uncoated_case = next(case for case in cases if case.name == "E") if uncoated_case is None else uncoated_case

    cases_by_name = {case.name: case for case in cases}
    plot_cases = [
        ("A", "peelcoating_price", peelcoating_values, "Peelcoating price"),
        ("B", "coating_cost", coating_cost_values, "Coating cost"),
        ("C", "peelcoating_price", peelcoating_values, "Peelcoating price"),
        ("D", "coating_cost", coating_cost_values, "Coating cost"),
        ("E", None, inactive_y_values, "Reference value"),
    ]

    coated_weight = peelcoated_uses / uses
    uncoated_weight = uncoated_uses / uses
    cmap = plt.cm.RdYlGn_r

    def grid_case_cost(case, sampled, max_uses_value):
        if case.name not in peelable_case_names:
            return case_cost_from_sample(
                case,
                sampled,
                max_uses_override=max_uses_value,
            )

        if case.name == "C":
            uncoated_split_case = case
            uncoated_cost_inputs = {
                "storage": sampled["storage"],
                "transport_cost": sampled["transport_cost"],
                "coating_cost": 0,
                "coating_internal": False,
                "decoating_time": 0,
                "max_uses": max_uses_value,
                "peelcoating_price": sampled["peelcoating_price"],
            }
        else:
            uncoated_split_case = uncoated_case
            uncoated_cost_inputs = {
                "storage": sampled["storage"],
                "transport_cost": sampled["transport_cost"],
                "coating_cost": uncoated_case.coating_cost,
                "decoating_time": uncoated_case.decoating_time,
                "max_uses": max_uses_value,
                "peelcoating_price": sampled["peelcoating_price"],
            }

        cost_inputs = {
            "storage": sampled["storage"],
            "transport_cost": sampled["transport_cost"],
            "coating_cost": case.coating_cost if case.name == "E" else sampled["coating_cost"],
            "decoating_time": case.decoating_time if case.name in ["D", "E"] else sampled["decoating_time"],
            "max_uses": case.max_uses if case.name == "D" else max_uses_value,
            "peelcoating_price": sampled["peelcoating_price"],
        }

        return case.calc_cost_with_use_split(
            uncoated_case=uncoated_split_case,
            cost_inputs=cost_inputs,
            uncoated_cost_inputs=uncoated_cost_inputs,
        )

    cutoff_case = cases_by_name[cutoff_case_name]
    explicit_row_cutoffs = {} if row_cutoffs is None else dict(row_cutoffs)
    calculated_row_cutoffs = {}
    for max_uses_value in max_uses_values:
        cutoff_sampled = {
            "storage": storage,
            "transport_cost": 85,
            "coating_cost": cutoff_case.coating_cost,
            "decoating_time": decoating_time,
            "max_uses": max_uses_value,
            "peelcoating_price": cutoff_case.peelcoating_price,
        }
        if max_uses_value in explicit_row_cutoffs:
            calculated_row_cutoffs[max_uses_value] = explicit_row_cutoffs[max_uses_value]
        elif cutoff is not None:
            calculated_row_cutoffs[max_uses_value] = cutoff
        else:
            calculated_row_cutoffs[max_uses_value] = case_cost_from_sample(
                cutoff_case,
                cutoff_sampled,
                max_uses_override=max_uses_value,
            )

    fig, axes = plt.subplots(
        len(max_uses_values),
        len(plot_cases),
        figsize=(8.27, 11.69),
        sharex=True,
    )
    row_images = []

    for row_idx, max_uses_value in enumerate(max_uses_values):
        row_cutoff = calculated_row_cutoffs[max_uses_value]
        row_plots = []
        row_min = np.inf
        standard_point_costs = {}

        for col_idx, (case_name, y_input, y_values, y_label) in enumerate(plot_cases):
            ax = axes[row_idx, col_idx]
            case = cases_by_name[case_name]
            Z = np.zeros((len(y_values), len(transport_values)))

            for y_idx, y_value in enumerate(y_values):
                for x_idx, transport_cost in enumerate(transport_values):
                    sampled = {
                        "storage": storage,
                        "transport_cost": transport_cost,
                        "coating_cost": case.coating_cost,
                        "decoating_time": decoating_time,
                        "max_uses": max_uses_value,
                        "peelcoating_price": case.peelcoating_price,
                    }
                    if y_input is not None:
                        sampled[y_input] = y_value

                    case_cost = grid_case_cost(case, sampled, max_uses_value)
                    Z[y_idx, x_idx] = np.nan if case_cost > row_cutoff else case_cost

            standard_sampled = {
                "storage": storage,
                "transport_cost": 85,
                "coating_cost": case.coating_cost,
                "decoating_time": decoating_time,
                "max_uses": max_uses_value,
                "peelcoating_price": case.peelcoating_price,
            }
            standard_point_costs[case_name] = grid_case_cost(case, standard_sampled, max_uses_value)

            if np.any(~np.isnan(Z)):
                row_min = min(row_min, np.nanmin(Z))

            row_plots.append((ax, case, case_name, y_input, y_values, y_label, col_idx, Z))

        if DEBUG_GRID_STANDARD_POINTS:
            print(f"Grid row max_uses={max_uses_value}, cutoff={row_cutoff:.2f}")
            for case_name, standard_cost in standard_point_costs.items():
                status = "below" if standard_cost <= row_cutoff else "above"
                print(f"  Case {case_name}: {standard_cost:.2f} ({status} cutoff)")

        row_min = 0 if np.isinf(row_min) else row_min
        row_norm = mcolors.Normalize(vmin=row_min, vmax=row_cutoff)
        row_im = None

        for ax, case, case_name, y_input, y_values, y_label, col_idx, Z in row_plots:
            im = ax.imshow(
                Z,
                origin="lower",
                aspect="auto",
                extent=[
                    transport_values.min(),
                    transport_values.max(),
                    y_values.min(),
                    y_values.max(),
                ],
                cmap=cmap,
                norm=row_norm,
            )
            row_im = im

            if row_idx == 0:
                ax.set_title(f"Case {case_name}", fontsize=9)
            if col_idx == 0:
                ax.set_ylabel(f"Max uses {max_uses_value}\ncutoff {row_cutoff:.0f}\n{y_label}", fontsize=8)
            elif y_input is None:
                ax.set_ylabel("")
                ax.set_yticks([])
            else:
                ax.set_yticks([5, 10, 15, 20])
            if row_idx == len(max_uses_values) - 1:
                ax.set_xlabel("Transport", fontsize=8)

            ax.axvline(85, linestyle="--", linewidth=0.7, color="black", alpha=0.6)
            if y_input is not None:
                base_y = case.peelcoating_price if y_input == "peelcoating_price" else case.coating_cost
                ax.axhline(base_y, linestyle="--", linewidth=0.7, color="black", alpha=0.6)
            ax.tick_params(labelsize=7)

        row_images.append(row_im)

    fig.subplots_adjust(right=0.86, top=0.94, bottom=0.06, hspace=0.35, wspace=0.25)
    for row_idx, row_im in enumerate(row_images):
        if row_im is None:
            continue
        row_pos = axes[row_idx, -1].get_position()
        cbar_ax = fig.add_axes([0.88, row_pos.y0, 0.012, row_pos.height])
        cbar = fig.colorbar(row_im, cax=cbar_ax)
        cbar.ax.tick_params(labelsize=6)

    fig.suptitle(
        f"Case cutoff grid, each row cutoff is Case {cutoff_case_name} at that max use",
        fontsize=12,
    )

    if show:
        plt.show()

    return fig, axes


# plot_transport_price_cutoff(cases, cutoff=(36.32*6))
plot_case_max_use_cutoff_grid(cases, row_cutoffs=CASE_D_ROW_CUTOFFS)


def run_monte_carlo(cases, n_sims=10000):
    results = []
    uncoated_case = next(case for case in cases if case.name == "E")

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
            row[case.name] = blended_case_cost(case, sampled, uncoated_case)

        results.append(row)

    return pd.DataFrame(results)


def print_monte_carlo_summary(df, case_names):
    print(df.head())
    inputs = ["storage", "transport_cost", "coating_cost", "decoating_time", "max_uses", "peelcoating_price"]

    print()
    print("Average inputs:")
    print(df[inputs].mean())

    print()
    print("Average cost per case:")
    print(df[case_names].mean())

    winner = df[case_names].idxmin(axis=1)
    print()
    print("Probability each case is cheapest:")
    print(winner.value_counts(normalize=True).sort_index())

    print(df[case_names].describe())

    for case in case_names:
        print(f"\n--- {case} ---")
        print(df[inputs + [case]].corr()[case].drop(case).sort_values(ascending=False))


def save_monte_carlo_results(df, case_names, output_dir="monte_carlo_output"):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    results_file = output_dir / "monte_carlo_results.csv"
    summary_file = output_dir / "monte_carlo_summary.json"

    df = df.copy()
    df["winner"] = df[case_names].idxmin(axis=1)
    df.to_csv(results_file, index=False)

    inputs = ["storage", "transport_cost", "coating_cost", "decoating_time", "max_uses", "peelcoating_price"]
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


#df = run_monte_carlo(cases, n_sims)
#case_names = [case.name for case in cases]
#print_monte_carlo_summary(df, case_names)
#results_file, summary_file = save_monte_carlo_results(df, case_names)
#print()
#print(f"Saved Monte Carlo results to: {results_file}")
#print(f"Saved Monte Carlo summary to: {summary_file}")


# a.plot_cost_below_cutoff(cutoff=4373.75)


print(f'{d.calc_cost()}')
print(f"Use split: {Case.evaluate_use_split()}")

print(f"d.cost_breakdown() = {d.cost_breakdown()}")

case_d_split_cost = d.calc_cost_with_use_split(
    uncoated_case=e,
    cost_inputs={
        "transport_cost": 85,
        "coating_cost": 9,
        "decoating_time": 0,
        "max_uses": 6,
        "peelcoating_price": d.peelcoating_price,
    }
)

print(case_d_split_cost)
