# run_experiments.py

import os
import glob
import argparse
import numpy as np
import pandas as pd
from plot_params import plot_exps, plot_box, plot_weakly_hard, plot_ilp_hard, plot_bar_response

# ============================================================
#  HELPER
# ============================================================
def compute_be_rates(base_dir):
    csv_files = glob.glob(os.path.join(base_dir, '*.csv'))
    if not csv_files:
        print(f"Warning: no files found at {base_dir}")
        return None, None, None

    rates_f1_f24  = []
    rates_f25_f48 = []
    rates_overall = []

    for csv_file in csv_files:
        try:
            df             = pd.read_csv(csv_file)
            df['Flow_Num'] = df['Flow'].str.extract(r'F(\d+)').astype(int)

            f1_f24   = df[df['Flow_Num'].between(1, 24)]
            be_total = (f1_f24['Class'] == 8).sum()
            be_sched = ((f1_f24['Class'] == 8) & (f1_f24['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_f1_f24.append(be_sched / be_total * 100)

            f25_f48  = df[df['Flow_Num'].between(25, 48)]
            be_total = (f25_f48['Class'] == 8).sum()
            be_sched = ((f25_f48['Class'] == 8) & (f25_f48['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_f25_f48.append(be_sched / be_total * 100)

            be_total = (df['Class'] == 8).sum()
            be_sched = ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
            if be_total > 0:
                rates_overall.append(be_sched / be_total * 100)

        except Exception as e:
            print(f"Error in {os.path.basename(csv_file)}: {e}")

    avg_f1_f24  = sum(rates_f1_f24)  / len(rates_f1_f24)  if rates_f1_f24  else 0
    avg_f25_f48 = sum(rates_f25_f48) / len(rates_f25_f48) if rates_f25_f48 else 0
    avg_overall = sum(rates_overall) / len(rates_overall)  if rates_overall else 0

    return avg_f1_f24, avg_f25_f48, avg_overall


# ============================================================
#  EXPERIMENT 1a — Schedulability Ratio
# ============================================================
def run_exp1_schedulability():
    base_dir_ilp       = 'Experiment_1/ILP/flows_{}/Results/'
    base_dir_heuristic = 'Experiment_1/Heuristic/flows_{}/Results/'
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_configs = [
        (16, 'Figures/Experiment_1/Fig_8_a.pdf'),
        (32, 'Figures/Experiment_1/Fig_8_c.pdf'),
        (48, 'Figures/Experiment_1/Fig_8_e.pdf'),
    ]

    for flow_count, output_file in flow_configs:
        records = []
        for u in utilization_values:
            folder_name      = f"flows_{flow_count}_u_{u}"
            ilp_folder       = os.path.join(base_dir_ilp.format(flow_count), folder_name)
            heuristic_folder = os.path.join(base_dir_heuristic.format(flow_count), folder_name)
            ilp_count        = len([f for f in os.listdir(ilp_folder)       if f.endswith('.csv')])
            heuristic_count  = len([f for f in os.listdir(heuristic_folder) if f.endswith('.csv')])
            records.append({
                'Utilization'                   : round(u, 2),
                'Schedulability Ratio ILP'      : ilp_count / 100,
                'Schedulability Ratio Heuristic': heuristic_count / 100,
            })
        data = pd.DataFrame(records)
        print(f"\nflow_count={flow_count}\n{data}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plot_exps(
            df=data,
            x_col='Utilization',
            y_cols=['Schedulability Ratio ILP', 'Schedulability Ratio Heuristic'],
            labels=['ILP', 'Lazy Search'],
            output_file=output_file,
            base_font_size=18,
            plot_size=(4.5, 3.1),
            xlabel='Utilization',
            ylabel='Schedulability \nRatio',
            xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
            yticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        )


# ============================================================
#  EXPERIMENT 1b — Optional Packet Admissibility Ratio
# ============================================================
def run_exp1_be():
    base_dir_ilp       = 'Experiment_1/ILP/flows_{}/Results/'
    base_dir_heuristic = 'Experiment_1/Heuristic/flows_{}/Results/'
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_configs = [
        (16, 'Figures/Experiment_1/Fig_8_b.pdf'),
        (32, 'Figures/Experiment_1/Fig_8_d.pdf'),
        (48, 'Figures/Experiment_1/Fig_8_f.pdf'),
    ]

    for flow_count, output_file in flow_configs:
        records = []
        for u in utilization_values:
            folder_name      = f"flows_{flow_count}_u_{u}"
            ilp_folder       = os.path.join(base_dir_ilp.format(flow_count), folder_name)
            ilp_files        = glob.glob(os.path.join(ilp_folder, '*.csv'))
            ilp_be_total     = 0
            ilp_be_sched     = 0
            for file_path in ilp_files:
                df            = pd.read_csv(file_path)
                ilp_be_total += (df['Class'] == 8).sum()
                ilp_be_sched += ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
            ilp_ratio        = (ilp_be_sched / ilp_be_total) if ilp_be_total > 0 else 0

            heuristic_folder = os.path.join(base_dir_heuristic.format(flow_count), folder_name)
            heuristic_files  = glob.glob(os.path.join(heuristic_folder, '*.csv'))
            heu_be_total     = 0
            heu_be_sched     = 0
            for file_path in heuristic_files:
                df            = pd.read_csv(file_path)
                heu_be_total += (df['Queue'] == 8).sum()
                heu_be_sched += ((df['Queue'] == 8) & (df['Scheduled'] == True)).sum()
            heuristic_ratio  = (heu_be_sched / heu_be_total) if heu_be_total > 0 else 0

            records.append({
                'Utilization'                     : round(u, 2),
                'BE Admissibility Ratio ILP'      : round(ilp_ratio, 4),
                'BE Admissibility Ratio Heuristic': round(heuristic_ratio, 4),
            })
        data = pd.DataFrame(records)
        print(f"\nflow_count={flow_count}\n{data}")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plot_exps(
            df=data,
            x_col='Utilization',
            y_cols=['BE Admissibility Ratio ILP', 'BE Admissibility Ratio Heuristic'],
            labels=['Optimal', 'Lazy Search'],
            output_file=output_file,
            base_font_size=18,
            plot_size=(4.5, 3.1),
            xlabel='Utilization',
            ylabel='Optional Packet \nAdmissibility Ratio',
            xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
            yticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        )


# ============================================================
#  EXPERIMENT 2 — Stress Test Box Plot + Table 1
# ============================================================
def run_exp2_stress():
    base_dir_time        = 'Experiment_2/Results/flows_48_u_0.8_{}'
    base_dir_constraints = 'Experiment_2/Results/flows_48_u_0.8_{}/stats'
    packet_vals          = ['p201', 'p252', 'p306', 'p351', 'p402', 'p450', 'p501']
    records              = []

    for p in packet_vals:
        time_folder        = base_dir_time.format(p)
        constraints_folder = base_dir_constraints.format(p)

        time_files = glob.glob(os.path.join(time_folder, '*.csv'))
        all_times  = []
        for csv_file in time_files:
            try:
                df = pd.read_csv(csv_file)
                if 'Solver_Execution_Time_Seconds' in df.columns:
                    all_times.append(df['Solver_Execution_Time_Seconds'].iloc[0])
            except Exception as e:
                print(f"Error in {p} time - {os.path.basename(csv_file)}: {e}")

        stats_files  = glob.glob(os.path.join(constraints_folder, '*.csv'))
        min_int_vars = float('inf')
        max_int_vars = float('-inf')
        for csv_file in stats_files:
            try:
                df = pd.read_csv(csv_file)
                if 'Integer_Variables' in df.columns:
                    val          = int(df['Integer_Variables'].iloc[0])
                    min_int_vars = min(min_int_vars, val)
                    max_int_vars = max(max_int_vars, val)
            except Exception as e:
                print(f"Error in {p} stats - {os.path.basename(csv_file)}: {e}")

        if not all_times:
            print(f"Warning: no solver time data for {p}")
            continue

        times_array   = np.array(all_times)
        q1            = np.percentile(times_array, 25)
        median        = np.percentile(times_array, 50)
        q3            = np.percentile(times_array, 75)
        iqr           = q3 - q1
        lower_bound   = q1 - 1.5 * iqr
        upper_bound   = q3 + 1.5 * iqr
        lower_whisker = np.min(times_array[times_array >= lower_bound])
        upper_whisker = np.max(times_array[times_array <= upper_bound])
        outliers      = times_array[(times_array < lower_bound) | (times_array > upper_bound)].tolist()

        records.append({
            'Packet'              : p,
            'Number of Constrains': [min_int_vars, max_int_vars],
            'q1'                  : q1,
            'median'              : median,
            'q3'                  : q3,
            'lower_whisker'       : lower_whisker,
            'upper_whisker'       : upper_whisker,
            'outlier'             : outliers,
            'min_int_vars'        : min_int_vars,
            'max_int_vars'        : max_int_vars,
        })

    data = pd.DataFrame(records)
    print("\n", data[['Packet', 'median', 'q1', 'q3', 'lower_whisker', 'upper_whisker']])

    # --- Table 1 ---
    table1 = pd.DataFrame({
        'Number of Packets'    : [int(p[1:]) for p in data['Packet']],
        'Number of Constraints': [f"[{int(row['min_int_vars'])}, {int(row['max_int_vars'])}]"
                                  for _, row in data.iterrows()],
    })
    os.makedirs('Figures/Experiment_2', exist_ok=True)
    table1.to_csv('Figures/Experiment_2/Table_1.csv', index=False)
    print("\nTable 1:")
    print(table1.to_string(index=False))

    # --- Plot ---
    os.makedirs('Figures/Experiment_2', exist_ok=True)
    plot_box(
        data=data,
        output_file='Figures/Experiment_2/Fig_9.pdf',
        base_font_size=20,
        plot_size=(10, 5.5),
        xlabel='Number of Constraints',
        ylabel='Time (s)',
        cutoff=3600,
        ylim=(-5, 4000),
    )


# ============================================================
#  EXPERIMENT 3 — OPAR Table
# ============================================================
def run_exp3_opar():
    _, _,            overall_conf1 = compute_be_rates('Experiment_3/No_weight/Results')
    f1_f24_conf2, f25_f48_conf2, overall_conf2 = compute_be_rates('Experiment_3/w_1_h_2_100/Results')
    f1_f24_conf3, f25_f48_conf3, overall_conf3 = compute_be_rates('Experiment_3/w_1_h_1_100/Results')

    print(f"\n{'Configuration':<15} {'Weighted OPAR (%)':>20} {'Non-Weighted OPAR (%)':>25} {'Total OPAR (%)':>18}")
    print("-" * 80)
    print(f"{'Conf. 1':<15} {'-':>20} {'-':>25} {overall_conf1:>17.2f}")
    print(f"{'Conf. 2':<15} {f1_f24_conf2:>20.2f} {f25_f48_conf2:>25.2f} {overall_conf2:>17.2f}")
    print(f"{'Conf. 3':<15} {f25_f48_conf3:>20.2f} {f1_f24_conf3:>25.2f} {overall_conf3:>17.2f}")
    # --- Save ---
    table = pd.DataFrame({
        'Configuration'        : ['Conf. 1', 'Conf. 2', 'Conf. 3'],
        'Weighted OPAR (%)'    : ['-',              f"{f1_f24_conf2:.2f}",  f"{f25_f48_conf3:.2f}"],
        'Non-Weighted OPAR (%)': ['-',              f"{f25_f48_conf2:.2f}", f"{f1_f24_conf3:.2f}"],
        'Total OPAR (%)'       : [f"{overall_conf1:.2f}", f"{overall_conf2:.2f}", f"{overall_conf3:.2f}"],
    })
    os.makedirs('Figures/Experiment_3', exist_ok=True)
    table.to_csv('Figures/Experiment_3/Table_2.csv', index=False)
    print("Saved: Figures/Experiment_3/Table_2.csv")

# ============================================================
#  EXPERIMENT 4 — ILP vs ILP_Hard
# ============================================================
def run_exp4_ilp_hard():
    base_dir_ilp      = 'Experiment_4/ILP/Results/'
    base_dir_ilp_hard = 'Experiment_4/ILP_Hard/Results/'
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_count         = 48

    records_mandatory = []
    records_be        = []

    for u in utilization_values:
        folder_name  = f"flows_{flow_count}_u_{u}"

        # --- ILP ---
        ilp_folder   = os.path.join(base_dir_ilp, folder_name)
        ilp_files    = glob.glob(os.path.join(ilp_folder, '*.csv'))
        ilp_be_total = 0
        ilp_be_sched = 0
        for file_path in ilp_files:
            try:
                df            = pd.read_csv(file_path)
                ilp_be_total += (df['Class'] == 8).sum()
                ilp_be_sched += ((df['Class'] == 8) & (df['Scheduled'] == 'Yes')).sum()
            except Exception as e:
                print(f"Error ILP {os.path.basename(file_path)}: {e}")
        ilp_mandatory_pct = 100.0
        ilp_be_pct        = (ilp_be_sched / ilp_be_total * 100) if ilp_be_total > 0 else 0

        # --- ILP_Hard ---
        hard_folder          = os.path.join(base_dir_ilp_hard, folder_name)
        hard_files           = glob.glob(os.path.join(hard_folder, '*.csv'))
        hard_mandatory_rates = []
        hard_be_rates        = []

        for file_path in hard_files:
            try:
                df              = pd.read_csv(file_path)
                total_mandatory = 0
                total_be        = 0
                mandatory_met   = 0
                be_met          = 0
                flows_sorted    = sorted(df['Flow'].unique(), key=lambda x: int(x[1:]))

                for flow in flows_sorted:
                    flow_packets            = df[df['Flow'] == flow].copy()
                    flow_packets['seq_num'] = flow_packets['Packet'].str.extract(r'P\d+_(\d+)').astype(int)
                    flow_packets            = flow_packets.sort_values('seq_num')

                    for idx, (_, packet) in enumerate(flow_packets.iterrows()):
                        is_mandatory = (idx % 3) in [0, 1]
                        if is_mandatory:
                            total_mandatory += 1
                            if packet['Deadline_Met'] == 'Yes':
                                mandatory_met += 1
                        else:
                            total_be += 1
                            if packet['Deadline_Met'] == 'Yes':
                                be_met += 1

                if total_mandatory > 0:
                    hard_mandatory_rates.append(mandatory_met / total_mandatory * 100)
                if total_be > 0:
                    hard_be_rates.append(be_met / total_be * 100)

            except Exception as e:
                print(f"Error ILP_Hard {os.path.basename(file_path)}: {e}")

        hard_mandatory_pct = sum(hard_mandatory_rates) / len(hard_mandatory_rates) if hard_mandatory_rates else 0
        hard_be_pct        = sum(hard_be_rates)        / len(hard_be_rates)        if hard_be_rates        else 0

        print(f"u={u}: ILP mandatory={ilp_mandatory_pct:.1f}%, Optional={ilp_be_pct:.2f}% | "
              f"ILP_Hard mandatory={hard_mandatory_pct:.2f}%, Optional={hard_be_pct:.2f}%")

        records_mandatory.append({
            'Utilization'          : round(u, 2),
            'ILP (Reserved)'       : ilp_mandatory_pct,
            'ILP_Hard (No Reserve)': hard_mandatory_pct,
        })
        records_be.append({
            'Utilization'          : round(u, 2),
            'ILP (Reserved)'       : ilp_be_pct,
            'ILP_Hard (No Reserve)': hard_be_pct,
        })

    data_mandatory = pd.DataFrame(records_mandatory)
    data_be        = pd.DataFrame(records_be)
    print("\nMandatory:\n", data_mandatory)
    print("\nOptional:\n",        data_be)

    os.makedirs('Figures/Experiment_4', exist_ok=True)
    plot_ilp_hard(
        df=data_mandatory,
        x_col='Utilization',
        y_cols=['ILP (Reserved)', 'ILP_Hard (No Reserve)'],
        labels=['Reserved Queue', 'No Reserved Queue'],
        output_file='Figures/Experiment_4/Fig_10_a.pdf',
        base_font_size=18, plot_size=(4.5, 3),
        xlabel='Utilization', ylabel='Admissibility (%)',
        xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
        yticks=[0, 25, 50, 75, 100], ylim=(-5, 105),
    )
    plot_ilp_hard(
        df=data_be,
        x_col='Utilization',
        y_cols=['ILP (Reserved)', 'ILP_Hard (No Reserve)'],
        labels=['Reserved Queue', 'No Reserved Queue'],
        output_file='Figures/Experiment_4/Fig_10_b.pdf',
        base_font_size=18, plot_size=(4.5, 3),
        xlabel='Utilization', ylabel='Admissibility (%)',
        xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
        yticks=[0, 25, 50, 75, 100], ylim=(-5, 105),
    )


# ============================================================
#  EXPERIMENT 5 — Weakly Hard Schedulability
# ============================================================
def run_exp5_weakly_hard():
    base_dirs = {
        'w0h1': 'Experiment_5/w_0_h_1/Results/',
        'w1h1': 'Experiment_5/w_1_h_1/Results/',
        'w1h2': 'Experiment_5/w_1_h_2/Results/',
        'w2h1': 'Experiment_5/w_2_h_1/Results/',
    }
    utilization_values = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    flow_count         = 48
    records            = []

    for u in utilization_values:
        folder_name = f"flows_{flow_count}_u_{u}"
        row         = {'Utilization': round(u, 2)}
        for key, base_dir in base_dirs.items():
            folder = os.path.join(base_dir, folder_name)
            if os.path.exists(folder):
                row[key] = len([f for f in os.listdir(folder) if f.endswith('.csv')]) / 100
            else:
                print(f"Warning: folder not found — {folder}")
                row[key] = 0.0
        records.append(row)

    data = pd.DataFrame(records)
    print(data)

    os.makedirs('Figures/Experiment_5', exist_ok=True)
    plot_weakly_hard(
        df=data,
        x_col='Utilization',
        y_cols=['w2h1', 'w1h1', 'w1h2', 'w0h1'],
        labels=[
            r'Weakly-Hard: $(w,h)=(2,1)$',
            r'Weakly-Hard: $(w,h)=(1,1)$',
            r'Weakly-Hard: $(w,h)=(1,2)$',
            r'Hard',
        ],
        output_file='Figures/Experiment_5/Fig_11.pdf',
        base_font_size=20, plot_size=(8.5, 5.5),
        xlabel='Total Utilization', ylabel='Schedulability Ratio',
        xticks=[0.4, 0.6, 0.8, 1.0, 1.2],
        yticks=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        ylim=(-0.05, 1.05),
    )


# ============================================================
#  HARDWARE EXPERIMENTS
# ============================================================
def run_hardware_exps():
    xticks = [1, 50, 100, 150, 200]
    yticks = [0, 0.5, 1.0]
    os.makedirs('Figures/Hardware_Exps', exist_ok=True)

    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_heuristic.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_a.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=False,
    )
    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_7q.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_b.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=False,
    )
    plot_bar_response(
        df=pd.read_csv('Hardware_Experiments/results_8q.csv'),
        output_file='Figures/Hardware_Exps/Fig_13_c.pdf',
        xticks=xticks, yticks=yticks,
        apply_class_override=True,
    )


# ============================================================
#  MAIN — argument parser
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run experiments and generate figures.')
    parser.add_argument(
        'experiment',
        choices=['exp1', 'exp2', 'exp3', 'exp4', 'exp5', 'hardware', 'all'],
        help='Which experiment to run'
    )
    args = parser.parse_args()

    if args.experiment == 'exp1':
        run_exp1_schedulability()
        run_exp1_be()
    elif args.experiment == 'exp2':
        run_exp2_stress()
    elif args.experiment == 'exp3':
        run_exp3_opar()
    elif args.experiment == 'exp4':
        run_exp4_ilp_hard()
    elif args.experiment == 'exp5':
        run_exp5_weakly_hard()
    elif args.experiment == 'hardware':
        run_hardware_exps()
    elif args.experiment == 'all':
        run_exp1_schedulability()
        run_exp1_be()
        run_exp2_stress()
        run_exp3_opar()
        run_exp4_ilp_hard()
        run_exp5_weakly_hard()
        run_hardware_exps()