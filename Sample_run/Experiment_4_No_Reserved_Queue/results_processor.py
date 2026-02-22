import pandas as pd
import os
import sys
import io
import gurobipy as gp

status_map = {
    gp.GRB.OPTIMAL: "Optimal",
    gp.GRB.INFEASIBLE: "Infeasible",
    gp.GRB.UNBOUNDED: "Unbounded",
    gp.GRB.TIME_LIMIT: "Time Limit Exceeded",
    gp.GRB.INTERRUPTED: "Interrupted",
    gp.GRB.SUBOPTIMAL: "Suboptimal",
    gp.GRB.NODE_LIMIT: "Node Limit Exceeded",
    gp.GRB.SOLUTION_LIMIT: "Solution Limit Exceeded",
}

def capture_model_stats(model):
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    try:
        model.printStats()
        stats_text = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    stats_dict = {}
    for line in stats_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key, value = key.strip(), value.strip()

            if key == "Variable types":
                for part in value.split(','):
                    part = part.strip()
                    if 'continuous' in part:
                        stats_dict['Continuous_Variables'] = int(part.split()[0])
                    elif 'integer' in part:
                        stats_dict['Integer_Variables'] = int(part.split('integer')[0].strip())
                        if '(' in part:
                            stats_dict['Binary_Variables'] = int(part.split('(')[1].split('binary')[0].strip())

            elif key in ("Matrix range", "Objective range", "Bounds range", "RHS range"):
                if '[' in value and ']' in value:
                    lo, hi = value.strip('[]').split(',')
                    stats_dict[f'{key}_Min'] = lo.strip()
                    stats_dict[f'{key}_Max'] = hi.strip()
                else:
                    stats_dict[key] = value

            elif 'rows' in value and 'columns' in value and 'nonzeros' in value:
                for part in value.split(','):
                    part = part.strip()
                    if 'rows' in part:
                        stats_dict['Rows'] = int(part.split()[0])
                    elif 'columns' in part:
                        stats_dict['Columns'] = int(part.split()[0])
                    elif 'nonzeros' in part:
                        stats_dict['Nonzeros'] = int(part.split()[0])
            else:
                try:
                    value = float(value) if ('.' in value and 'e' not in value.lower()) else int(value) if value.isdigit() else value
                except ValueError:
                    pass
                stats_dict[key] = value
        else:
            if 'model' in line.lower() and "'" in line:
                stats_dict['Model_Name'] = line.split("'")[1]
            elif line in ('MIP', 'LP', 'QP', 'MILP', 'MIQP'):
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

    solver_status = status_map.get(model.status, f"Unknown ({model.status})")

    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        packet_class = pkt["Class"]
        flow_name = pkt["Flow"]

        try:
            start = int(start_times[pkt_id].x)
        except AttributeError:
            start = None

        base = {
            "Flow": flow_name,
            "Packet": pkt_id,
            "Class": packet_class,
            "Arrival": arrival,
            "Deadline": deadline,
            "Execution_Time": exec_time,
            "Solver_Execution_Time_Seconds": execution_time,
            "Solver_Execution_Time_Minutes": execution_time / 60,
            "Solver_Status": solver_status,
            "Objective_Value": model.objVal,
            "Stopping_Reason": stopping_reason,
        }

        if start is not None:
            gate_close = start + exec_time
            response_time = gate_close - arrival
            met = gate_close <= deadline

            gcl_log.append({
                "Packet": pkt_id,
                "Class": packet_class,
                "Arrival": arrival,
                "Gate_Open": start,
                "Gate_Close": gate_close,
                "Deadline": deadline,
                "Response_Time": response_time,
            })

            all_packets_log.append({**base,
                "Gate_Open": start,
                "Gate_Close": gate_close,
                "Response_Time": response_time,
                "Status": "Scheduled - Deadline Met" if met else "Scheduled - Deadline Missed",
                "Scheduled": "Yes",
                "Deadline_Met": "Yes" if met else "No",
            })
        else:
            all_packets_log.append({**base,
                "Gate_Open": None,
                "Gate_Close": None,
                "Response_Time": None,
                "Status": "Not Scheduled (Incomplete Solution)",
                "Scheduled": "No",
                "Deadline_Met": "N/A",
            })

    all_packets_df = pd.DataFrame(all_packets_log).sort_values(by=["Flow", "Arrival"]).reset_index(drop=True)
    gcl_df = pd.DataFrame(gcl_log).sort_values(by="Gate_Open").reset_index(drop=True) if gcl_log else pd.DataFrame()

    return all_packets_df, gcl_df

def save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder):
    os.makedirs(results_folder, exist_ok=True)
    base_name = os.path.splitext(input_filename)[0]
    filepath = os.path.join(results_folder, f'all_packets_status_{base_name}.csv')
    all_packets_df.to_csv(filepath, index=False)
    print(f"All packets status saved to '{filepath}'")

def print_summary(all_packets_df, model, execution_time, stopping_reason):
    total = len(all_packets_df)
    scheduled = len(all_packets_df[all_packets_df["Scheduled"] == "Yes"])
    violations = len(all_packets_df[all_packets_df["Deadline_Met"] == "No"])

    print(f"\n=== PACKET SCHEDULING SUMMARY ===")
    print(f"Total: {total} | Scheduled: {scheduled} | Unscheduled: {total - scheduled} | Deadline violations: {violations}")

    for status, count in all_packets_df['Status'].value_counts().items():
        print(f"  {status}: {count}")

    if violations > 0:
        print(f"\nWARNING: {violations} packets missed their deadlines!")
        print(all_packets_df[all_packets_df["Deadline_Met"] == "No"][
            ["Packet", "Class", "Arrival", "Deadline", "Gate_Close", "Response_Time"]
        ].to_string(index=False))
    else:
        print("\nAll scheduled packets meet their deadlines ✓")

    print(f"\n=== SOLVER PERFORMANCE ===")
    print(f"Execution Time: {execution_time:.4f}s ({execution_time/60:.2f} min)")
    print(f"Status: {status_map.get(model.status, f'Unknown ({model.status})')}")
    print(f"Objective Value: {model.objVal:.0f}")
    print(f"Stopping Reason: {stopping_reason}")

def handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename=None, results_folder='Results'):
    if model.status == gp.GRB.OPTIMAL or model.SolCount > 0:
        print(f"\nSolution found! Status: {status_map.get(model.status, f'Unknown ({model.status})')}")
        print(f"Objective value: {model.objVal:.0f}")

        all_packets_df, gcl_df = process_results(
            model, packet_instances, start_times, is_scheduled, execution_time, stopping_reason, number_flows)
        save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder)
        print_summary(all_packets_df, model, execution_time, stopping_reason)

        if gap_history:
            print(f"\n=== GAP STABILITY (last 5 checks) ===")
            for entry in gap_history[-5:]:
                print(f"  Check {entry.get('check', 'N/A')}: Gap={entry.get('gap', 0)*100:.3f}%, "
                      f"Solution={entry.get('solution', 'N/A')}, Time={entry.get('time', 0):.0f}s")

    elif model.status == gp.GRB.INFEASIBLE:
        print("No feasible solution found!")
        try:
            model.computeIIS()
            model.write("infeasible.ilp")
            print("IIS written to 'infeasible.ilp'")
        except Exception as e:
            print(f"Error computing IIS: {e}")
    else:
        print(f"Optimization ended with status {status_map.get(model.status, f'Unknown ({model.status})')}")
        print(f"Solution count: {model.SolCount}")