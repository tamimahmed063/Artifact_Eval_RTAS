import gurobipy as gp
from gurobipy import GRB
import re

def add_constraints(model, packet_instances, start_times, is_scheduled, solver_params):
    """
    Add all scheduling constraints to the Gurobi model with redundancy elimination.
    Simplified version treating all packets as TT packets.
    
    Args:
        model (gp.Model): Gurobi model to add constraints to.
        packet_instances (list): List of packet instance dictionaries.
        start_times (dict): Start time variables for each packet.
        is_scheduled (dict): Scheduling decision variables (not used in simplified version).
        solver_params (dict): Solver parameters including Cipg, t_max, and M.
        
    Returns:
        dict: Statistics about constraints added and redundancy elimination.
    """
    Cipg = solver_params['Cipg']
    M = solver_params['M']
    
    # Track packet pairs that already have ordering constraints to avoid redundancy
    constrained_pairs = set()
    max_execution_time = max(pkt["Execution Time"] for pkt in packet_instances)
    
    # Statistics tracking
    stats = {
        'arrival_constraints': 0,
        'response_time_constraints': 0,
        'fifo_constraints': 0,
        'tie_break_constraints': 0,
        'edf_constraints': 0,
        'physical_constraints': 0,
        'skipped_constraints': 0,
        'total_constrained_pairs': 0,
        'total_packet_instances': len(packet_instances)
    }
    
    # 1. Arrival Constraints and Response Time Constraints
    for pkt in packet_instances:
        pkt_id = pkt["Packet"]
        arrival_time = pkt["Arrival"]
        deadline = pkt["Deadline"]
        exec_time = pkt["Execution Time"]
        s = start_times[pkt_id]
        
        # Arrival constraint: packet can't start before it arrives
        model.addConstr(s >= arrival_time, name=f"arrival_{pkt_id}")
        stats['arrival_constraints'] += 1
        
        response_time = s + exec_time - arrival_time
        model.addConstr(response_time >= exec_time, name=f"min_response_{pkt_id}")
        stats['response_time_constraints'] += 1
        
        # Deadline constraint commented out as in reference code
        # model.addConstr(s + exec_time <= deadline, name=f"deadline_{pkt_id}")
    
    # 2. FIFO Constraints within Same Queue
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Arrival"] < pkt2["Arrival"] and 
                pkt1["Class"] == pkt2["Class"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                
                # Earlier packet must finish before later packet starts
                model.addConstr(s1 + e1 + Cipg <= s2, name=f"fifo_{stats['fifo_constraints']}")
                stats['fifo_constraints'] += 1
                
                # Track this pair as constrained
                constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
    
    # 3. Tie-Breaking Constraints for Same Queue and Same Arrival Time
    def get_flow_priority(flow_name):
        """Extract numeric priority from flow name (e.g., 'Flow1' -> 1)."""
        match = re.search(r'\d+', flow_name)
        return int(match.group()) if match else 999
    
    # Add flow priority to packet instances for easier access
    for pkt in packet_instances:
        pkt["Flow_Priority"] = get_flow_priority(pkt["Flow"])
    
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Class"] == pkt2["Class"] and
                pkt1["Arrival"] == pkt2["Arrival"]):
                
                s1 = start_times[pkt1["Packet"]]
                s2 = start_times[pkt2["Packet"]]
                e1 = pkt1["Execution Time"]
                e2 = pkt2["Execution Time"]
                
                # Determine packet priority using tie-breaking rules (simplified logic)
                should_pkt1_go_first = False
                if pkt1["Deadline"] < pkt2["Deadline"]:
                    should_pkt1_go_first = True
                elif pkt1["Deadline"] > pkt2["Deadline"]:
                    should_pkt1_go_first = False
                else:
                    # Equal deadlines - check execution time
                    if pkt1["Execution Time"] > pkt2["Execution Time"]:
                        should_pkt1_go_first = True
                    elif pkt1["Execution Time"] < pkt2["Execution Time"]:
                        should_pkt1_go_first = False
                    else:
                        # Equal execution times - check flow priority
                        if pkt1["Flow_Priority"] < pkt2["Flow_Priority"]:
                            should_pkt1_go_first = True
                
                # Apply ordering constraint based on tie-breaking decision
                if should_pkt1_go_first:
                    model.addConstr(s1 + e1 + Cipg <= s2, 
                                  name=f"tie_break_tt_{stats['tie_break_constraints']}")
                    constrained_pairs.add((pkt1["Packet"], pkt2["Packet"]))
                else:
                    model.addConstr(s2 + e2 + Cipg <= s1, 
                                  name=f"tie_break_tt_{stats['tie_break_constraints']}")
                    constrained_pairs.add((pkt2["Packet"], pkt1["Packet"]))
                
                stats['tie_break_constraints'] += 1
    
    # 4. Earliest Deadline First (EDF) for packets with different arrival times
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances):
            if (pkt1["Packet"] != pkt2["Packet"] and
                pkt1["Deadline"] < pkt2["Deadline"] and
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
    
    # 5. Physical Medium Non-overlap Constraints (only for unconstrained pairs)
    for i, pkt1 in enumerate(packet_instances):
        for j, pkt2 in enumerate(packet_instances[i+1:], start=i+1):
            if pkt1["Packet"] == pkt2["Packet"]:
                continue
            
            # Check if this pair already has ordering constraints
            pair1 = (pkt1["Packet"], pkt2["Packet"])
            pair2 = (pkt2["Packet"], pkt1["Packet"])
            
            if pair1 in constrained_pairs or pair2 in constrained_pairs:
                stats['skipped_constraints'] += 1
                continue  # Skip - already constrained by FIFO, tie-breaking, or EDF
                
            s1 = start_times[pkt1["Packet"]]
            s2 = start_times[pkt2["Packet"]]
            e1 = pkt1["Execution Time"]
            e2 = pkt2["Execution Time"]
            
            # Binary variable to choose ordering (simplified - no class-specific logic)
            order = model.addVar(vtype=GRB.BINARY, name=f"order_{stats['physical_constraints']}")
            
            # Non-overlap constraints
            model.addConstr(s1 + e1 + Cipg <= s2 + M * order, name=f"nonoverlap1_{stats['physical_constraints']}")
            model.addConstr(s2 + e2 + Cipg <= s1 + M * (1 - order), name=f"nonoverlap2_{stats['physical_constraints']}")
            
            stats['physical_constraints'] += 1
    
    # Update total constrained pairs
    stats['total_constrained_pairs'] = len(constrained_pairs)
    
    # Print constraint statistics
    print(f"\n=== CONSTRAINT STATISTICS ===")
    print(f"Arrival constraints: {stats['arrival_constraints']}")
    print(f"Response time constraints: {stats['response_time_constraints']}")
    print(f"FIFO constraints: {stats['fifo_constraints']}")
    print(f"Tie-break constraints: {stats['tie_break_constraints']}")
    print(f"EDF constraints: {stats['edf_constraints']}")
    print(f"Physical constraints: {stats['physical_constraints']}")
    print(f"Skipped constraints: {stats['skipped_constraints']}")
    print(f"Total constrained pairs: {stats['total_constrained_pairs']}")
    
    return stats