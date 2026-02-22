import gurobipy as gp
from gurobipy import GRB
import time


class GapStabilityCallback:
    def __init__(self, max_stable_iterations=5, check_interval=20000):
        self.max_stable_iterations = max_stable_iterations
        self.check_interval = check_interval
        self.last_gap = None
        self.stable_count = 0
        self.iteration_count = 0
        self.gap_history = []

    def __call__(self, model, where):
        if where == GRB.Callback.MIP:
            self.iteration_count += 1

            if self.iteration_count % self.check_interval == 0:
                objbst = model.cbGet(GRB.Callback.MIP_OBJBST)
                objbnd = model.cbGet(GRB.Callback.MIP_OBJBND)
                nodcnt = model.cbGet(GRB.Callback.MIP_NODCNT)
                runtime = model.cbGet(GRB.Callback.RUNTIME)

                if objbst != GRB.INFINITY and objbst != 0:
                    current_gap = abs(objbst - objbnd) / abs(objbst)
                    rounded_gap = round(current_gap * 1000, 1)

                    print(f"Check #{len(self.gap_history)+1}: Gap: {current_gap*100:.3f}%, "
                          f"Solution: {int(objbst)}, Nodes: {int(nodcnt)}, Time: {runtime:.0f}s")

                    if self.last_gap is None:
                        self.last_gap = rounded_gap
                        self.stable_count = 1
                    elif abs(rounded_gap - self.last_gap) < 0.1:
                        self.stable_count += 1
                        print(f"   → Gap stable for {self.stable_count} consecutive checks")
                    else:
                        self.stable_count = 1
                        self.last_gap = rounded_gap
                        print("   → Gap changed, resetting counter")

                    self.gap_history.append({
                        'check': len(self.gap_history) + 1,
                        'gap': current_gap,
                        'solution': int(objbst),
                        'bound': objbnd,
                        'nodes': int(nodcnt),
                        'time': runtime
                    })

                    if self.stable_count >= self.max_stable_iterations:
                        print(f"\nSTOPPING: Gap stable at {current_gap*100:.3f}% "
                              f"for {self.stable_count} consecutive checks")
                        print(f"Best solution found: {int(objbst)} BE packets")
                        model.terminate()


def setup_objective(model, packet_instances, is_scheduled):
    flow_weights = {"F1": 1.0}
    weighted_be_sum = 0
    be_packet_count = 0

    for pkt in packet_instances:
        if pkt["Class"] == 8:
            flow_name = pkt["Flow"]
            weight = flow_weights.get(flow_name, 1.0)
            weighted_be_sum += weight * is_scheduled[pkt["Packet"]]
            be_packet_count += 1

    if be_packet_count > 0:
        model.setObjective(weighted_be_sum, GRB.MAXIMIZE)
        print(f"Maximizing weighted sum of {be_packet_count} BE packets")
    else:
        model.setObjective(0, GRB.MAXIMIZE)

    return be_packet_count


def solve_model(model, gap_callback):

    start_time = time.time()

    try:
        model.optimize(gap_callback)
    except KeyboardInterrupt:
        print("Optimization interrupted by user")

    execution_time = time.time() - start_time

    if model.status == GRB.OPTIMAL:
        stopping_reason = "Proven Optimal (Gap = 0%)"
    elif gap_callback.stable_count >= gap_callback.max_stable_iterations:
        stopping_reason = f"Gap Stable for {gap_callback.stable_count} Checks"
    else:
        stopping_reason = f"Gurobi Status: {model.status}"

    return execution_time, gap_callback.gap_history, stopping_reason