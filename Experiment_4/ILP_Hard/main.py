import os
import gc
import sys
import traceback
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


def get_results_folder(path):
    if os.path.isfile(path):
        subfolder = os.path.basename(os.path.dirname(path))
    elif os.path.isdir(path):
        subfolder = os.path.basename(os.path.normpath(path))
    else:
        subfolder = ''

    # Strip everything after the utilization value e.g. flows_48_u_1.0_8queues -> flows_48_u_1.0
    segments = subfolder.split('_')
    try:
        u_idx = segments.index('u')
        subfolder = '_'.join(segments[:u_idx + 2])
    except ValueError:
        pass

    return os.path.join('Results', subfolder) if subfolder else 'Results'


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py <input_folder>          # run all CSVs in folder")
        print("  python main.py <path/to/file.csv>      # run a single file")
        return

    path = sys.argv[1]

    if os.path.isfile(path):
        if not path.endswith('.csv'):
            print(f"Error: '{path}' is not a CSV file.")
            return
        results_folder = get_results_folder(path)
        os.makedirs(results_folder, exist_ok=True)
        print(f"Results will be saved to: '{results_folder}'")
        process_single_file(path, results_folder)

    elif os.path.isdir(path):
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print(f"No CSV files found in '{path}'")
            return

        results_folder = get_results_folder(path)
        os.makedirs(results_folder, exist_ok=True)
        print(f"Found {len(csv_files)} CSV files in '{path}'")
        print(f"Results will be saved to: '{results_folder}'")
        successful, failed = 0, 0

        for i, csv_file in enumerate(csv_files, 1):
            print(f"\nProcessing {i}/{len(csv_files)}: {csv_file}")
            if process_single_file(os.path.join(path, csv_file), results_folder):
                successful += 1
            else:
                failed += 1
            gc.collect()

        print(f"\nBatch Summary — Total: {len(csv_files)} | Successful: {successful} | Failed: {failed}")

    else:
        print(f"Error: '{path}' is not a valid file or directory.")


if __name__ == "__main__":
    main()