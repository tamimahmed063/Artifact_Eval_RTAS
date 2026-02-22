import pandas as pd
import os
import sys
import io
import gurobipy as gp
from gurobipy import GRB


def capture_model_stats(model):
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()

    try:
        model.printStats()
        stats_text = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    stats_dict = {}
    lines = stats_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key, value = key.strip(), value.strip()

            if key == "Variable types":
                parts = value.split(',')
                for part in parts:
                    part = part.strip()
                    if 'continuous' in part:
                        stats_dict['Continuous_Variables'] = int(part.split()[0])
                    elif 'integer' in part:
                        if '(' in part:
                            stats_dict['Integer_Variables'] = int(part.split('integer')[0].strip())
                            stats_dict['Binary_Variables'] = int(part.split('(')[1].split('binary')[0].strip())
                        else:
                            stats_dict['Integer_Variables'] = int(part.split()[0])

            elif key in ["Matrix range", "Objective range", "Bounds range", "RHS range"]:
                if '[' in value:
                    min_val, max_val = value.strip('[]').split(',')
                    stats_dict[f'{key}_Min'] = min_val.strip()
                    stats_dict[f'{key}_Max'] = max_val.strip()
                else:
                    stats_dict[key] = value

            elif 'rows' in value and 'columns' in value and 'nonzeros' in value:
                parts = value.split(',')
                for part in parts:
                    if 'rows' in part:
                        stats_dict['Rows'] = int(part.split()[0])
                    elif 'columns' in part:
                        stats_dict['Columns'] = int(part.split()[0])
                    elif 'nonzeros' in part:
                        stats_dict['Nonzeros'] = int(part.split()[0])

            else:
                try:
                    if '.' in value and 'e' not in value.lower():
                        value = float(value)
                    elif value.isdigit():
                        value = int(value)
                except ValueError:
                    pass
                stats_dict[key] = value

        else:
            if 'model' in line.lower() and "'" in line:
                stats_dict['Model_Name'] = line.split("'")[1]
            elif line in ['MIP', 'LP', 'QP', 'MILP', 'MIQP']:
                stats_dict['Problem_Type'] = line

    return stats_dict, stats_text


def save_model_stats_to_csv(stats_dict, input_filename, results_folder):
    stats_df = pd.DataFrame([stats_dict])
    stats_df['Input_File'] = input_filename

    stats_folder = os.path.join(results_folder, 'stats')
    os.makedirs(stats_folder, exist_ok=True)

    base_name = os.path.splitext(input_filename)[0]
    stats_filepath = os.path.join(stats_folder, f'model_stats_{base_name}.csv')

    stats_df.to_csv(stats_filepath, index=False)
    print(f"Model statistics saved to '{stats_filepath}'")

    return stats_filepath


def process_results(model, packet_instances, start_times, is_scheduled, execution_time, stopping_reason, number_flows):
    all_packets_log = []
    gcl_log = []

    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        packet_class = pkt["Class"]
        flow_name = pkt["Flow"]

        try:
            is_sched = is_scheduled[pkt_id].x >= 0.5 if packet_class == 8 else True
        except AttributeError:
            is_sched = False if packet_class == 8 else True

        if is_sched:
            try:
                start = int(start_times[pkt_id].x)
                gate_close = start + exec_time
                response_time = gate_close - arrival
                status = "Scheduled - Deadline Met" if gate_close <= deadline else "Scheduled - Deadline Missed"

                gcl_log.append({
                    "Packet": pkt_id,
                    "Class": packet_class,
                    "Arrival": arrival,
                    "Gate Open": start,
                    "Gate Close": gate_close,
                    "Deadline": deadline,
                    "Response Time": response_time
                })
            except AttributeError:
                start = gate_close = response_time = None
                status = "Scheduled - Invalid Start Time"
        else:
            start = gate_close = response_time = None
            status = "Optional Packets- Not Scheduled" if packet_class == 8 else "TT - Not Scheduled (ERROR!)"

        all_packets_log.append({
            "Flow": flow_name,
            "Packet": pkt_id,
            "Class": packet_class,
            "Arrival": arrival,
            "Deadline": deadline,
            "Execution Time": exec_time,
            "Gate Open": start,
            "Gate Close": gate_close,
            "Response Time": response_time,
            "Status": status,
            "Scheduled": "Yes" if is_sched else "No",
            "Deadline Met": "Yes" if is_sched and gate_close is not None and gate_close <= deadline else "No" if is_sched else "N/A",
            "Solver_Execution_Time_Seconds": execution_time,
            "Solver_Execution_Time_Minutes": execution_time / 60,
            "Solver_Status": model.status,
            "Objective_Value": model.objVal if model.SolCount > 0 else None,
            "Stopping_Reason": stopping_reason
        })

    all_packets_df = pd.DataFrame(all_packets_log).sort_values(by=["Flow", "Arrival"]).reset_index(drop=True)
    gcl_df = pd.DataFrame(gcl_log).sort_values(by="Gate Open").reset_index(drop=True) if gcl_log else pd.DataFrame()

    return all_packets_df, gcl_df


def save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder):
    os.makedirs(results_folder, exist_ok=True)

    base_name = os.path.splitext(input_filename)[0]
    filepath = os.path.join(results_folder, f'all_packets_status_{base_name}.csv')

    all_packets_df.to_csv(filepath, index=False)
    print(f"All packets status saved to '{filepath}'")


def print_summary(all_packets_df, model, execution_time):
    total_packets = len(all_packets_df)
    scheduled_packets = len(all_packets_df[all_packets_df["Scheduled"] == "Yes"])
    scheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "Yes")])
    scheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "Yes")])
    unscheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "No")])
    unscheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "No")])
    deadline_violations = len(all_packets_df[all_packets_df["Deadline Met"] == "No"])

    print("\n=== PACKET SCHEDULING SUMMARY ===")
    print(f"Total packets: {total_packets}")
    print(f"Scheduled packets: {scheduled_packets}")
    print(f"  - Mandatory packets scheduled: {scheduled_tt}")
    print(f"  - Optional packets scheduled: {scheduled_be}")
    print(f"Unscheduled packets: {total_packets - scheduled_packets}")
    print(f"  - Mandatory packets unscheduled: {unscheduled_tt}")
    print(f"  - Optional packets unscheduled: {unscheduled_be}")
    print(f"Deadline violations: {deadline_violations}")

    print("\n=== STATUS BREAKDOWN ===")
    for status, count in all_packets_df['Status'].value_counts().items():
        print(f"{status}: {count}")

    if deadline_violations == 0:
        print("\nAll scheduled packets meet their deadlines")

    print("\n=== SAMPLE OF ALL PACKETS STATUS ===")
    display_cols = ["Flow", "Packet", "Class", "Status", "Solver_Execution_Time_Minutes", "Stopping_Reason"]
    print(all_packets_df[display_cols].head(10).to_string(index=False))

    print("\n=== SOLVER PERFORMANCE SUMMARY ===")
    print(f"Execution Time: {execution_time:.4f} seconds ({execution_time/60:.2f} minutes)")
    print(f"Solver Status: {model.status}")
    print(f"Objective Value: {model.objVal if model.SolCount > 0 else 'N/A'}")
    print(f"Stopping Reason: {all_packets_df['Stopping_Reason'].iloc[0]}")


def handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename, results_folder):
    valid_solution_statuses = [GRB.OPTIMAL, GRB.INTERRUPTED, GRB.NODE_LIMIT, GRB.TIME_LIMIT, GRB.SOLUTION_LIMIT, GRB.SUBOPTIMAL]

    print(f"Optimization ended with status {model.status}")

    if model.status in valid_solution_statuses and model.SolCount > 0:
        print(f"Objective value: {model.objVal}")

        all_packets_df, gcl_df = process_results(
            model, packet_instances, start_times, is_scheduled,
            execution_time, stopping_reason, number_flows
        )

        save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder)
        print_summary(all_packets_df, model, execution_time)

    elif model.status == GRB.INFEASIBLE:
        print("No feasible solution found")
        model.computeIIS()
        model.write("infeasible.ilp")

    else:
        print(f"No solution available. Status: {model.status}")