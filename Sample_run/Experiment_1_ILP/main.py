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
        print(f"\nProcessing file: {input_filename}")

        df = data_loader.load_flow_data(file_path)
        hyperperiod = data_loader.compute_hyperperiod(df)

        flows = model_config.create_flow_dictionaries(df)

        model, solver_params = model_config.setup_gurobi_model(hyperperiod)

        start_times, is_scheduled, packet_instances = model_config.generate_packet_instances(model, flows, hyperperiod)

        constraints.add_constraints(model, packet_instances, start_times, is_scheduled, solver_params)

        be_packet_count = solver.setup_objective(model, packet_instances, is_scheduled)

        gap_callback = solver.GapStabilityCallback(max_stable_iterations=10, check_interval=5000)

        stats_dict, _ = results_processor.capture_model_stats(model)

        results_processor.save_model_stats_to_csv(stats_dict, input_filename, results_folder)
        execution_time, gap_history, stopping_reason = solver.solve_model(model, gap_callback)
        number_flows = len(df['Flow'])

        results_processor.handle_results(model, packet_instances, start_times, is_scheduled, execution_time, gap_history, stopping_reason, number_flows, input_filename, results_folder)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

    finally:
        if model is not None:
            try:
                model.dispose()
            except:
                pass

        if df is not None: del df
        if flows is not None: del flows
        if packet_instances is not None: del packet_instances
        if start_times is not None: del start_times
        if is_scheduled is not None: del is_scheduled
        if gap_callback is not None: del gap_callback

        gc.collect()


def main():
    results_folder = 'Results'  ######### Change as your need

    if len(sys.argv) > 1:
        file_path = sys.argv[1]

        if not os.path.isfile(file_path):
            print(f"Error: File '{file_path}' not found.")
            return

        if not file_path.endswith('.csv'):
            print(f"Error: '{file_path}' is not a CSV file.")
            return

        os.makedirs(results_folder, exist_ok=True)
        print(f"Running single file mode: {file_path}")
        process_single_file(file_path, results_folder)
        return

    # Otherwise, fall back to folder scanning
    input_folder = 'input_csvs'  ######### Change according to the inputs location
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(results_folder, exist_ok=True)

    csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]

    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    print(f"Found {len(csv_files)} CSV files")

    successful = 0
    failed = 0

    for i, csv_file in enumerate(csv_files, 1):
        print(f"\nProcessing {i}/{len(csv_files)}: {csv_file}")
        file_path = os.path.join(input_folder, csv_file)

        if process_single_file(file_path, results_folder): successful += 1
        else: failed += 1

        gc.collect()

    print("\nBatch Summary")
    print(f"Total: {len(csv_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()