import argparse
import json
from pathlib import Path

import pandas as pd


SUMMARY_FILE = Path("monte_carlo_output/monte_carlo_summary.json")
CSV_FILE = Path("monte_carlo_output/monte_carlo_results.csv")
OUTPUT_FILE = Path("monte_carlo_output/monte_carlo_summary_tables.xlsx")


def load_summary(summary_file):
    with summary_file.open(encoding="utf-8") as file:
        return json.load(file)


def load_results(csv_file):
    return pd.read_csv(csv_file)


def find_input_columns(df, case_names):
    ignored_columns = {"sim", "winner", *case_names}
    return [
        column
        for column in df.columns
        if column not in ignored_columns and pd.api.types.is_numeric_dtype(df[column])
    ]


def make_tables(summary, results_df=None):
    if results_df is not None:
        input_columns = find_input_columns(results_df, summary["case_names"])
        average_inputs_data = results_df[input_columns].mean()
    else:
        average_inputs_data = pd.Series(summary.get("average_inputs", {}))

    average_inputs = (
        pd.Series(average_inputs_data, name="Average input")
        .to_frame()
        .round(2)
    )

    average_costs = (
        pd.Series(summary["average_cost_per_case"], name="Average cost")
        .to_frame()
        .round(2)
    )

    cheapest_probability = (
        pd.Series(summary["probability_each_case_is_cheapest"], name="Probability cheapest")
        .to_frame()
        .round(3)
    )

    descriptive_stats = (
        pd.DataFrame(summary["cost_descriptive_statistics"])
        .T
        .round(2)
    )

    correlations = (
        pd.DataFrame(summary["input_correlations_by_case"])
        .T
        .round(3)
    )

    return {
        "Average Inputs": average_inputs,
        "Average Costs": average_costs,
        "Cheapest Probability": cheapest_probability,
        "Cost Statistics": descriptive_stats,
        "Correlations": correlations,
    }


def save_tables_to_excel(tables, output_file):
    output_file.parent.mkdir(exist_ok=True)

    with pd.ExcelWriter(output_file) as writer:
        for sheet_name, table in tables.items():
            table.to_excel(writer, sheet_name=sheet_name)


def parse_args():
    parser = argparse.ArgumentParser(description="Convert Monte Carlo JSON and CSV output to Excel tables.")
    parser.add_argument("--summary", type=Path, default=SUMMARY_FILE, help="Path to the summary JSON file.")
    parser.add_argument("--csv", type=Path, default=CSV_FILE, help="Path to the results CSV file.")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Path to the Excel output file.")
    return parser.parse_args()


def main():
    args = parse_args()
    summary = load_summary(args.summary)
    results_df = load_results(args.csv)
    tables = make_tables(summary, results_df)
    save_tables_to_excel(tables, args.output)
    print(f"Saved Excel summary to: {args.output}")


if __name__ == "__main__":
    main()
