import os
import gc
import sys
import data_loader
import model_config
import constraints
import solver
import results_processor

def process_single_file(file_path, results_folder):
    model = None
    df = None
    flows = None
    packet_instances = None
    start_times = None
    is_scheduled = None
    gap_callback = None

    try:
        input_filename = os.path.basename(file_path)
        print(f"\nProcessing: {input_filename}")

        df = data_loader.load_flow_data(file_path)
        hyperperiod = data_loader.compute_hyperperiod(df)

        flows = model_config.create_flow_dictionaries(df)
        model, solver_params = model_config.setup_gurobi_model(hyperperiod)

        t_max = solver_params.get('t_max', hyperperiod)
        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(
            model, flows, hyperperiod, t_max)

        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)

        solver.setup_objective(model, packet_instances, start_times)
        gap_callback = solver.GapStabilityCallback(max_stable_iterations=5, check_interval=5000)

        stats_dict, stats_text = results_processor.capture_model_stats(model)
        print(stats_text)
        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder)

        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)

        results_processor.handle_results(
            model, packet_instances, start_times, is_scheduled,
            execution_time, gap_history, stopping_reason, len(df['Flow']),
            input_filename, results_folder
        )

        return True

    except Exception as e:
        import traceback
        print(f"Error processing {file_path}: {e}")
        traceback.print_exc()
        return False

    finally:
        if model is not None:
            try:
                model.dispose()
            except:
                pass
        for var in [df, flows, packet_instances, start_times, is_scheduled, gap_callback]:
            if var is not None:
                del var
        gc.collect()


def main():
    input_folder = 'input_csvs/' ######## Change according to .csv location
    results_folder = 'Results/'  ######## Change according to where you want to save

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(results_folder, exist_ok=True)

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            sys.exit(1)
        csv_files = [file_path]
        use_full_path = True
    else:
        csv_files = [os.path.join(input_folder, f)
                     for f in os.listdir(input_folder) if f.endswith('.csv')]
        use_full_path = True
        if not csv_files:
            print(f"No CSV files found in {input_folder}")
            return

    successful, failed = 0, 0

    for i, file_path in enumerate(csv_files, 1):
        print(f"\n{'='*50}")
        print(f"File {i}/{len(csv_files)}: {file_path}")
        print(f"{'='*50}")

        if process_single_file(file_path, results_folder):
            successful += 1
        else:
            failed += 1

        gc.collect()

    print(f"\n{'='*30}")
    print(f"Total: {len(csv_files)} | Successful: {successful} | Failed: {failed}")
    print(f"Results saved to: {results_folder}")
    gc.collect()


if __name__ == "__main__":
    main()