import gurobipy as gp
from gurobipy import GRB
import re

def add_constraints(model, packet_instances, start_times, is_scheduled, solver_params):
    Cipg = solver_params['Cipg']
    M = solver_params['M']
    
    constrained_pairs = set()
    
    stats = {
        'fifo_constraints': 0,
        'tie_break_constraints': 0,
        'edf_constraints': 0,
        'physical_constraints': 0,
        'skipped_constraints': 0,
        'total_constrained_pairs': 0,
        'total_packet_instances': len(packet_instances)
    }
    
    max_execution_time = max(pkt["Execution Time"] for pkt in packet_instances)
    
    ## Temporal Constraints
    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival_time = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        s = start_times[pkt_id]
        
        if pkt["Class"] == 8:
            sched = is_scheduled[pkt_id]
            model.addConstr(s >= arrival_time * sched, name=f"arrival_{pkt_id}")
            model.addConstr(s + exec_time <= deadline + M * (1 - sched), name=f"deadline_{pkt_id}")
        else:
            model.addConstr(s >= arrival_time, name=f"arrival_{pkt_id}")
            model.addConstr(s + exec_time <= deadline, name=f"deadline_{pkt_id}")
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Arrival"] < pkt2["Arrival"] and pkt1["Class"] == pkt2["Class"]):
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                model.addConstr(s1 + e1 + Cipg <= s2, name=f"fifo_{stats['fifo_constraints']}")
                stats['fifo_constraints'] += 1
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    def get_flow_priority(flow_name):
        match = re.search(r'\d+', flow_name)
        return int(match.group()) if match else 999
    
    for pkt in packet_instances:
        pkt["Flow_Priority"] = get_flow_priority(pkt["Flow"])
    

    ## Order constraints
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Class"] == pkt2["Class"] and
                pkt1["Arrival"] == pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                should_pkt1_go_first = (
                    pkt1["Deadline"] < pkt2["Deadline"] or
                    (pkt1["Deadline"] == pkt2["Deadline"] and pkt1["Execution Time"] > pkt2["Execution Time"]) or
                    (pkt1["Deadline"] == pkt2["Deadline"] and pkt1["Execution Time"] == pkt2["Execution Time"] and pkt1["Flow_Priority"] < pkt2["Flow_Priority"])
                )
                
                if pkt1["Class"] == 8:
                    sched1 = is_scheduled[pkt1["Packet"]]
                    sched2 = is_scheduled[pkt2["Packet"]]
                    
                    both_sched = model.addVar(vtype=GRB.BINARY, name=f"tie_both_sched_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched <= sched1, name=f"tie_both1_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched <= sched2, name=f"tie_both2_{stats['tie_break_constraints']}")
                    model.addConstr(both_sched >= sched1 + sched2 - 1, name=f"tie_both_and_{stats['tie_break_constraints']}")
                    
                    if should_pkt1_go_first:
                        model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - both_sched), name=f"tie_break_be_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                    else:
                        model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - both_sched), name=f"tie_break_be_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                        
                else:
                    if should_pkt1_go_first:
                        model.addConstr(s1 + e1 + Cipg <= s2, name=f"tie_break_tt_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                    else:
                        model.addConstr(s2 + e2 + Cipg <= s1, name=f"tie_break_tt_{stats['tie_break_constraints']}")
                        constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                
                stats['tie_break_constraints'] += 1
    
    ## Non preemption constraints
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Deadline"] < pkt2["Deadline"] and
                pkt1["Class"] != 8 and pkt2["Class"] != 8 and
                pkt1["Arrival"] != pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                # Binary variables for overlap detection
                overlap = model.addVar(vtype=GRB.BINARY, name=f"overlap_{stats['edf_constraints']}")
                before1 = model.addVar(vtype=GRB.BINARY, name=f"before1_{stats['edf_constraints']}")
                before2 = model.addVar(vtype=GRB.BINARY, name=f"before2_{stats['edf_constraints']}")
                
                # Define before1 and before2 based on packet timing
                model.addConstr(s1 + e1 <= s2 + M * before1, name=f"before1_def_{stats['edf_constraints']}")
                model.addConstr(s2 + e2 <= s1 + M * before2, name=f"before2_def_{stats['edf_constraints']}")
                
                model.addConstr(overlap <= 1 - before1 + before2, name=f"overlap_upper1_{stats['edf_constraints']}")
                model.addConstr(overlap <= 1 + before1 - before2, name=f"overlap_upper2_{stats['edf_constraints']}")
                model.addConstr(overlap >= before1 + before2 - 1, name=f"overlap_lower1_{stats['edf_constraints']}")
                model.addConstr(overlap >= 1 - before1 - before2, name=f"overlap_lower2_{stats['edf_constraints']}")
                
                # If they overlap, earlier deadline goes first
                model.addConstr(s1 + e1 + Cipg <= s2 + M * (1 - overlap), name=f"edf_{stats['edf_constraints']}")
                stats['edf_constraints'] += 1
                
                # Track this pair as constrained
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    


    ## Non-overlaping constraints
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances[i+1:], start=i+1):
            if pkt1["Packet"] == pkt2["Packet"]:
                continue
            
            pair1 = (pkt1["Packet"], pkt2["Packet"])
            pair2 = (pkt2["Packet"], pkt1["Packet"])
            
            if pair1 in constrained_pairs or pair2 in constrained_pairs:
                stats['skipped_constraints'] += 1
                continue
                
            s1 = start_times[pkt1["Packet"]]
            s2 = start_times[pkt2["Packet"]]
            e1 = pkt1["Execution Time"]
            e2 = pkt2["Execution Time"]
            c1 = pkt1["Class"]
            c2 = pkt2["Class"]
            
            sched1 = is_scheduled[pkt1["Packet"]] if c1 == 8 else 1
            sched2 = is_scheduled[pkt2["Packet"]] if c2 == 8 else 1
            
            order = model.addVar(vtype=GRB.BINARY, name=f"order_{stats['physical_constraints']}")
            
            if c1 != 8 and c2 != 8:
                model.addConstr(s1 + e1 + Cipg <= s2 + M * order, name=f"nonoverlap1_{stats['physical_constraints']}")
                model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - order), name=f"nonoverlap2_{stats['physical_constraints']}")
                
            elif c1 == 8 and c2 == 8:
                both_sched = model.addVar(vtype=GRB.BINARY, name=f"both_sched_{stats['physical_constraints']}")
                model.addConstr(both_sched <= sched1, name=f"both_sched1_{stats['physical_constraints']}")
                model.addConstr(both_sched <= sched2, name=f"both_sched2_{stats['physical_constraints']}")
                model.addConstr(both_sched >= sched1 + sched2 - 1, name=f"both_sched_and_{stats['physical_constraints']}")
                
                model.addConstr(
                    s1 + e1 + Cipg <= s2 + M * (1 - both_sched) + M * order,
                    name=f"be_nonoverlap1_{stats['physical_constraints']}"
                )
                model.addConstr(
                    s2 + e2 + Cipg <= s1 + M * (1 - both_sched) + M * (1 - order),
                    name=f"be_nonoverlap2_{stats['physical_constraints']}"
                )
                
            elif c1 == 8 and c2 != 8:
                model.addConstr(
                    s1 + e1 + max_execution_time <= s2 + M * (1 - sched1) + M * order,
                    name=f"be_tt_nonoverlap1_{stats['physical_constraints']}"
                )
                model.addConstr(
                    s2 + e2 + Cipg <= s1 + M * (1 - sched1) + M * (1 - order),
                    name=f"be_tt_nonoverlap2_{stats['physical_constraints']}"
                )
                
            elif c1 != 8 and c2 == 8:
                model.addConstr(
                    s1 + e1 + Cipg <= s2 + M * (1 - sched2) + M * order,
                    name=f"tt_be_nonoverlap1_{stats['physical_constraints']}"
                )
                model.addConstr(
                    s2 + e2 + max_execution_time <= s1 + M * (1 - sched2) + M * (1 - order),
                    name=f"tt_be_nonoverlap2_{stats['physical_constraints']}"
                )
            
            stats['physical_constraints'] += 1