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
            key = key.strip()
            value = value.strip()
            
            if key == "Variable types":
                parts = value.split(',')
                
                for part in parts:
                    part = part.strip()
                    if 'continuous' in part:
                        continuous_count = int(part.split()[0])
                        stats_dict['Continuous_Variables'] = continuous_count
                    elif 'integer' in part:
                        if '(' in part and ')' in part:
                            integer_part = part.split('integer')[0].strip()
                            integer_count = int(integer_part)
                            stats_dict['Integer_Variables'] = integer_count
                            
                            binary_part = part.split('(')[1].split('binary')[0].strip()
                            binary_count = int(binary_part)
                            stats_dict['Binary_Variables'] = binary_count
                        else:
                            integer_count = int(part.split()[0])
                            stats_dict['Integer_Variables'] = integer_count
                            
            elif key == "Matrix range" or key == "Objective range" or key == "Bounds range" or key == "RHS range":
                if '[' in value and ']' in value:
                    range_values = value.strip('[]').split(',')
                    if len(range_values) == 2:
                        min_val = range_values[0].strip()
                        max_val = range_values[1].strip()
                        stats_dict[f'{key}_Min'] = min_val
                        stats_dict[f'{key}_Max'] = max_val
                else:
                    stats_dict[key] = value
                    
            elif 'rows' in value and 'columns' in value and 'nonzeros' in value:
                parts = value.split(',')
                for part in parts:
                    part = part.strip()
                    if 'rows' in part:
                        rows = int(part.split()[0])
                        stats_dict['Rows'] = rows
                    elif 'columns' in part:
                        columns = int(part.split()[0])
                        stats_dict['Columns'] = columns
                    elif 'nonzeros' in part:
                        nonzeros = int(part.split()[0])
                        stats_dict['Nonzeros'] = nonzeros
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
                model_name = line.split("'")[1]
                stats_dict['Model_Name'] = model_name
            elif line in ['MIP', 'LP', 'QP', 'MILP', 'MIQP']:
                stats_dict['Problem_Type'] = line
    
    return stats_dict, stats_text

def save_model_stats_to_csv(stats_dict, input_filename, results_folder):
    stats_df = pd.DataFrame([stats_dict])
    stats_df['Input_File'] = input_filename
    
    stats_folder = os.path.join(results_folder, 'stats')
    os.makedirs(stats_folder, exist_ok=True)
    
    base_name = os.path.splitext(input_filename)[0]
    stats_filename = f'model_stats_{base_name}.csv'
    stats_filepath = os.path.join(stats_folder, stats_filename)
    
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
        
        is_sched = False
        try:
            is_sched = is_scheduled[pkt_id].x >= 0.5 if packet_class == 8 else True
        except AttributeError:
            print(f"Warning: Unable to access scheduling decision for {pkt_id}. Assuming not scheduled.")
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
                print(f"Warning: Unable to access start time for {pkt_id}. Marking as unscheduled.")
                start = None
                gate_close = None
                response_time = None
                status = "Scheduled - Invalid Start Time"
        else:
            start = None
            gate_close = None
            response_time = None
            status = "BE - Not Scheduled" if packet_class == 8 else "TT - Not Scheduled (ERROR!)"
        
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
    all_packets_filename = f'all_packets_status_{base_name}.csv'
    all_packets_filepath = os.path.join(results_folder, all_packets_filename)
    all_packets_df.to_csv(all_packets_filepath, index=False)
    print(f"All packets status saved to '{all_packets_filepath}'")

def print_summary(all_packets_df, model, execution_time):
    total_packets = len(all_packets_df)
    scheduled_packets = len(all_packets_df[all_packets_df["Scheduled"] == "Yes"])
    scheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "Yes")])
    scheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "Yes")])
    unscheduled_tt = len(all_packets_df[(all_packets_df["Class"] != 8) & (all_packets_df["Scheduled"] == "No")])
    unscheduled_be = len(all_packets_df[(all_packets_df["Class"] == 8) & (all_packets_df["Scheduled"] == "No")])
    deadline_violations = len(all_packets_df[all_packets_df["Deadline Met"] == "No"])
    
    print(f"\n=== PACKET SCHEDULING SUMMARY ===")
    print(f"Total packets: {total_packets}")
    print(f"Scheduled packets: {scheduled_packets}")
    print(f"  - TT packets scheduled: {scheduled_tt}")
    print(f"  - BE packets scheduled: {scheduled_be}")
    print(f"Unscheduled packets: {total_packets - scheduled_packets}")
    print(f"  - TT packets unscheduled: {unscheduled_tt} {'(ERROR!)' if unscheduled_tt > 0 else ''}")
    print(f"  - BE packets unscheduled: {unscheduled_be}")
    print(f"Deadline violations: {deadline_violations}")
    
    status_counts = all_packets_df['Status'].value_counts()
    print(f"\n=== STATUS BREAKDOWN ===")
    for status, count in status_counts.items():
        print(f"{status}: {count}")
    
    if deadline_violations > 0:
        print(f"\nWARNING: {deadline_violations} packets missed their deadlines!")
        violated_packets = all_packets_df[all_packets_df["Deadline Met"] == "No"]
        print("Packets that missed deadlines:")
        print(violated_packets[["Packet", "Class", "Arrival", "Deadline", "Gate Close", "Response Time"]])
    else:
        print("\nAll scheduled packets meet their deadlines ✓")
    
    print(f"\n=== SAMPLE OF ALL PACKETS STATUS ===")
    display_cols = ["Flow", "Packet", "Class", "Status", "Solver_Execution_Time_Minutes", "Stopping_Reason"]
    print(all_packets_df[display_cols].head(10).to_string(index=False))
    
    print(f"\n=== SOLVER PERFORMANCE SUMMARY ===")
    print(f"Execution Time: {execution_time:.4f} seconds ({execution_time/60:.2f} minutes)")
    print(f"Solver Status: {model.status}")
    print(f"Objective Value: {model.objVal if model.SolCount > 0 else 'N/A'}")
    print(f"Stopping Reason: {all_packets_df['Stopping_Reason'].iloc[0]}")

def handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename, results_folder):
    valid_solution_statuses = [
        GRB.OPTIMAL,
        GRB.INTERRUPTED,
        GRB.NODE_LIMIT,
        GRB.TIME_LIMIT,
        GRB.SOLUTION_LIMIT,
        GRB.SUBOPTIMAL
    ]
    
    print(f"Optimization ended with status {model.status}")
    status_names = {
        2: "OPTIMAL", 8: "NODE_LIMIT", 9: "TIME_LIMIT", 
        10: "SOLUTION_LIMIT", 11: "INTERRUPTED", 13: "SUBOPTIMAL"
    }
    status_name = status_names.get(model.status, f"UNKNOWN({model.status})")
    print(f"Status name: {status_name}")
    print(f"Solution count: {model.SolCount}")
    
    if model.status in valid_solution_statuses and model.SolCount > 0:
        print(f"\nSolution found! Status: {model.status}")
        print(f"Objective value: {model.objVal}")
        
        all_packets_df, gcl_df = process_results(model, packet_instances, start_times, is_scheduled, 
                                                execution_time, stopping_reason, number_flows)
        save_results(all_packets_df, gcl_df, number_flows, input_filename, results_folder)
        print_summary(all_packets_df, model, execution_time)
        
        if gap_history:
            print(f"\n=== GAP STABILITY ANALYSIS ===")
            print(f"Total gap checks performed: {len(gap_history)}")
            print(f"Final stable count: {max(entry['check'] for entry in gap_history) if gap_history else 0}")
            print("\nGap History (last 5 checks):")
            for entry in gap_history[-5:]:
                print(f"  Check {entry['check']}: Gap={entry['gap']*100:.3f}%, "
                      f"Solution={entry['solution']}, Time={entry['time']:.0f}s")
                
    elif model.status == GRB.INFEASIBLE:
        print("No feasible solution found!")
        model.computeIIS()
        model.write("infeasible.ilp")
        print("IIS written to infeasible.ilp")
    
    else:
        print(f"No solution available. Status: {model.status}, Solution count: {model.SolCount}")