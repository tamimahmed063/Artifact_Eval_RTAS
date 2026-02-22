import os
import gc
import sys
from process_single_file import process_single_file


def get_results_folder(file_path, base_results='Results'):
    filename = os.path.splitext(os.path.basename(file_path))[0]
    segments = filename.split('_')
    try:
        u_idx = segments.index('u')
        group = '_'.join(segments[:u_idx + 2])
    except ValueError:
        group = filename
    root = os.path.normpath(file_path).split(os.sep)[0]
    return os.path.join(root, base_results, group)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py <input_folder>      # run all CSVs in folder")
        print("  python main.py <path/to/file.csv>  # run a single file")
        return

    path = sys.argv[1]
    successful, failed = 0, 0

    if os.path.isfile(path):
        if not path.endswith('.csv'):
            print(f"Error: '{path}' is not a CSV file.")
            return
        results_folder = get_results_folder(path)
        os.makedirs(results_folder, exist_ok=True)
        print(f"Results will be saved to: '{results_folder}'")
        if process_single_file(path, results_folder):
            successful += 1
        else:
            failed += 1

    elif os.path.isdir(path):
        csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
        if not csv_files:
            print(f"No CSV files found in '{path}'")
            return

        print(f"Found {len(csv_files)} CSV files in '{path}'")

        for i, csv_file in enumerate(csv_files, 1):
            file_path = os.path.join(path, csv_file)
            results_folder = get_results_folder(file_path)
            os.makedirs(results_folder, exist_ok=True)
            print(f"\nProcessing {i}/{len(csv_files)}: {csv_file}")
            print(f"Results will be saved to: '{results_folder}'")
            if process_single_file(file_path, results_folder):
                successful += 1
            else:
                failed += 1
            gc.collect()

    else:
        print(f"Error: '{path}' is not a valid file or directory.")
        return

    print(f"\nBatch Summary — Total: {successful + failed} | Successful: {successful} | Failed: {failed}")


if __name__ == "__main__":
    main()