import gurobipy as gp
from gurobipy import GRB
import time


class GapStabilityCallback:
    def __init__(self, max_stable_iterations=5, check_interval=2000):
        self.max_stable_iterations = max_stable_iterations
        self.check_interval = check_interval
        self.last_gap = None
        self.stable_count = 0
        self.iteration_count = 0
        self.gap_history = []

    def __call__(self, model, where):
        if where != GRB.Callback.MIP:
            return

        self.iteration_count += 1
        if self.iteration_count % self.check_interval != 0:
            return

        objbst = model.cbGet(GRB.Callback.MIP_OBJBST)
        objbnd = model.cbGet(GRB.Callback.MIP_OBJBND)
        nodcnt = model.cbGet(GRB.Callback.MIP_NODCNT)
        runtime = model.cbGet(GRB.Callback.RUNTIME)

        if objbst == GRB.INFINITY or objbst == 0:
            return

        current_gap = abs(objbst - objbnd) / abs(objbst)
        rounded_gap = round(current_gap * 1000, 1)

        print(f"Check #{len(self.gap_history)+1}: Gap={current_gap*100:.3f}%, "
              f"Response Time={int(objbst)}, Nodes={int(nodcnt)}, Time={runtime:.0f}s")

        if self.last_gap is None:
            self.last_gap = rounded_gap
            self.stable_count = 1
        elif abs(rounded_gap - self.last_gap) < 1:
            self.stable_count += 1
            print(f"  → Stable for {self.stable_count} consecutive checks")
        else:
            self.stable_count = 1
            self.last_gap = rounded_gap
            print(f"  → Gap changed, resetting counter")

        self.gap_history.append({
            'check': len(self.gap_history) + 1,
            'gap': current_gap,
            'solution': int(objbst),
            'bound': objbnd,
            'nodes': int(nodcnt),
            'time': runtime,
        })

        if self.stable_count >= self.max_stable_iterations:
            print(f"\nSTOPPING: Gap stable at {current_gap*100:.3f}% for {self.stable_count} checks")
            model.terminate()


def setup_objective(model, packet_instances, start_times):
    response_times = [
        start_times[pkt["Packet"]] + pkt["Execution Time"] - pkt["Arrival"]
        for pkt in packet_instances
    ]
    model.setObjective(gp.quicksum(response_times), GRB.MINIMIZE)
    return len(response_times)


def solve_model(model, gap_callback):
    start = time.time()
    try:
        model.optimize(gap_callback)
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user.")

    execution_time = time.time() - start

    print(f"\nExecution time: {execution_time:.4f}s ({execution_time/60:.2f} min)")

    if model.status == GRB.OPTIMAL:
        stopping_reason = "Proven Optimal (Gap = 0%)"
    elif gap_callback.stable_count >= gap_callback.max_stable_iterations:
        stopping_reason = f"Gap Stable for {gap_callback.stable_count} Checks"
    else:
        stopping_reason = f"Gurobi Status: {model.status}"

    print(f"Stopping reason: {stopping_reason}")

    return execution_time, gap_callback.gap_history, stopping_reason