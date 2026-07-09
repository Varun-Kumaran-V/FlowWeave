import os
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = "sim/results"

def load_summary(path):
    df = pd.read_csv(path)
    return {row["metric"]: row["mean"] for _, row in df.iterrows()}


def plot_control_vs_load():
    scenarios = {
        "bg5": "multiseed_bg5_final/summary.csv",
        "bg10": "multiseed_bg10/summary.csv",
        "bg20": "multiseed_bg20/summary.csv",
    }

    loads = []
    fw_ctrl = []

    for label, file in scenarios.items():
        data = load_summary(os.path.join(RESULTS_DIR, file))
        loads.append(int(label.replace("bg","")))
        fw_ctrl.append(data["fw_ctrl_msgs"])

    plt.figure()
    plt.plot(loads, fw_ctrl, marker="o")
    plt.xlabel("Background load (flows/ms)")
    plt.ylabel("Control messages (FlowWeave)")
    plt.title("Controller Load vs Background Traffic")
    plt.grid(True)

    plt.savefig(os.path.join(RESULTS_DIR, "plot_ctrl_vs_load.png"))
    print("Saved plot_ctrl_vs_load.png")


def plot_tcam_conditions():
    scenarios = {
        "baseline": "multiseed_bg5_final/summary.csv",
        "bursty": "multiseed_onoff/summary.csv",
        "skew": "multiseed_skew5/summary.csv",
    }

    names = []
    tcam = []

    for name, file in scenarios.items():
        data = load_summary(os.path.join(RESULTS_DIR, file))
        names.append(name)
        tcam.append(data["fw_tcam_peak"])

    plt.figure()
    plt.bar(names, tcam)
    plt.ylabel("TCAM Peak Entries")
    plt.title("TCAM Usage Across Traffic Scenarios")
    plt.grid(axis="y")

    plt.savefig(os.path.join(RESULTS_DIR, "plot_tcam_conditions.png"))
    print("Saved plot_tcam_conditions.png")


def plot_pareto():
    df = pd.read_csv(os.path.join(RESULTS_DIR, "targeted_deriv_final/targeted_summary.csv"))

    plt.figure()
    plt.scatter(df["tcam_peak_mean"], df["ctrl_reduction_mean"])

    plt.xlabel("TCAM Peak")
    plt.ylabel("Control Message Reduction")
    plt.title("Pareto Frontier: TCAM vs Control Reduction")
    plt.grid(True)

    plt.savefig(os.path.join(RESULTS_DIR, "plot_pareto.png"))
    print("Saved plot_pareto.png")


if __name__ == "__main__":
    plot_control_vs_load()
    plot_tcam_conditions()
    plot_pareto()