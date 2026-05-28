from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


CSV_FILE = Path("monte_carlo_output/monte_carlo_results.csv")
OUTPUT_FILE = Path("monte_carlo_output/monte_carlo_case_prices.png")

CASE_COLOURS = {
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


def load_results(csv_file):
    return pd.read_csv(csv_file)


def find_case_columns(df):
    ignored_columns = {
        "sim",
        "storage",
        "transport_cost",
        "coating_cost",
        "decoating_time",
        "max_uses",
        "peelcoating_price",
        "peelcoating_time",
        "winner",
    }

    return [
        column
        for column in df.columns
        if column not in ignored_columns and pd.api.types.is_numeric_dtype(df[column])
    ]


def plot_case_prices(df, case_columns, output_file=None, show=True):
    fig, ax = plt.subplots(figsize=(12, 6))

    for case in case_columns:
        ax.plot(
            df["sim"],
            df[case],
            label=f"Case {case}",
            color=CASE_COLOURS.get(case),
            linewidth=1,
            alpha=0.55,
        )

    ax.set_xlabel("Simulation")
    ax.set_ylabel("Price")
    ax.set_title("Monte Carlo prices by case")
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(title="Case", ncols=min(len(case_columns), 5))

    fig.tight_layout()

    if output_file is not None:
        output_file.parent.mkdir(exist_ok=True)
        fig.savefig(output_file, dpi=200)

    if show:
        plt.show()

    return fig, ax


def main():
    df = load_results(CSV_FILE)
    case_columns = find_case_columns(df)
    plot_case_prices(df, case_columns, output_file=OUTPUT_FILE)
    print(f"Saved line plot to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
