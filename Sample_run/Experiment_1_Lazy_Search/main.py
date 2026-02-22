import os
import gc
import sys
from process_single_file import process_single_file

def main():
    input_folder = 'input_csvs'
    output_folder = 'Results'

    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    if len(sys.argv) > 1:
        csv_files = [sys.argv[1]]
        use_full_path = True
    else:
        csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]
        use_full_path = False

    if not csv_files:
        print("No CSV files found.")
        return

    successful = 0
    failed = 0

    for csv_file in csv_files:
        file_path = csv_file if use_full_path else os.path.join(input_folder, csv_file)
        result = process_single_file(file_path, output_folder)

        if result is not False:
            successful += 1
        else:
            failed += 1

        gc.collect()

    print(f"\nBatch Summary")
    print(f"Total: {len(csv_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()