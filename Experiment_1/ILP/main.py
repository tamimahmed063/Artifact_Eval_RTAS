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
        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(model, flows, hyperperiod)
        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)
        solver.setup_objective(model, packet_instances, is_scheduled)
        gap_callback = solver.GapStabilityCallback(max_stable_iterations=10, check_interval=5000)

        stats_dict, _ = results_processor.capture_model_stats(model)
        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder)

        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)

        results_processor.handle_results(
            model, packet_instances, start_times, is_scheduled,
            execution_time, gap_history, stopping_reason,
            len(df['Flow']), input_filename, results_folder
        )
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
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
    # Derive results folder from input path
    # e.g. flows_16/input_csvs/flows_16_u_0.4_01.csv -> flows_16/Results/flows_16_u_0.4
    # e.g. flows_16/input_csvs/                       -> flows_16/Results
    parts = os.path.normpath(path).split(os.sep)

    # Find the root (e.g. "flows_16") as the first part
    root = parts[0] if parts else 'Results'

    if os.path.isfile(path):
        filename = os.path.splitext(parts[-1])[0]       # flows_16_u_0.4_01
        segments = filename.split('_')
        # Reconstruct up to and including utilization: flows_16_u_0.4
        try:
            u_idx = segments.index('u')
            group = '_'.join(segments[:u_idx + 2])       # flows_16_u_0.4
        except ValueError:
            group = filename
        return os.path.join(root, 'Results', group)

    elif os.path.isdir(path):
        return os.path.join(root, 'Results')

    return 'Results'


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py <input_folder>          # run all CSVs in folder")
        print("  python main.py <path/to/file.csv>      # run a single file")
        return

    path = sys.argv[1]
    results_folder = get_results_folder(path)
    os.makedirs(results_folder, exist_ok=True)
    print(f"Results will be saved to: '{results_folder}'")

    if os.path.isfile(path):
        if not path.endswith('.csv'):
            print(f"Error: '{path}' is not a CSV file.")
            return
        process_single_file(path, results_folder)

    elif os.path.isdir(path):
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print(f"No CSV files found in '{path}'")
            return

        print(f"Found {len(csv_files)} CSV files in '{path}'")
        successful, failed = 0, 0

        for i, csv_file in enumerate(csv_files, 1):
            print(f"\nProcessing {i}/{len(csv_files)}: {csv_file}")
            file_path = os.path.join(path, csv_file)
            file_results_folder = get_results_folder(file_path)
            os.makedirs(file_results_folder, exist_ok=True)
            print(f"Results will be saved to: '{file_results_folder}'")
            if process_single_file(file_path, file_results_folder):
                successful += 1
            else:
                failed += 1
            gc.collect()

        print(f"\nBatch Summary — Total: {len(csv_files)} | Successful: {successful} | Failed: {failed}")

    else:
        print(f"Error: '{path}' is not a valid file or directory.")


if __name__ == "__main__":
    main()