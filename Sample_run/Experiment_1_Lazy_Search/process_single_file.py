import pandas as pd
import math
import os
from functools import reduce

def process_single_file(file_path, output_folder):
    try:
        filename = os.path.basename(file_path)
        base_filename = os.path.splitext(filename)[0]

        df = pd.read_csv(file_path)

        required_columns = ['Flow', 'Period', 'Deadline', 'Execution Time', 'Queue', 'w', 'h']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"ERROR: Missing required columns: {missing_columns}")
            return False

        periods = df['Period'].tolist()
        w = df['w'].tolist()
        h = df['h'].tolist()
        k = [w[i] + h[i] for i in range(len(w))]
        products = [k[i] * periods[i] for i in range(len(k))]

        def lcm(a, b):
            return abs(a * b) // math.gcd(a, b)

        hyperperiod = reduce(lcm, products)

        flows = []
        for _, row in df.iterrows():
            flows.append({
                "Flow": row["Flow"],
                "Period": int(row["Period"]),
                "Deadline": int(row["Deadline"]),
                "Execution Time": int(row["Execution Time"]),
                "Queue": int(row["Queue"]),
                "w": int(row["w"]),
                "h": int(row["h"])
            })

        packet_instances = []
        for flow in flows:
            T = flow['Period']
            L = flow['Execution Time']
            D = flow['Deadline']
            base_class = flow['Queue']
            h_val = flow['h']
            w_val = flow['w']
            group_size = h_val + w_val
            num_instances = hyperperiod // T

            for j in range(num_instances):
                arrival = j * T
                deadline = j * T + D
                group_index = j % group_size
                queue_class = base_class if group_index < h_val else 8

                packet_instances.append({
                    "Flow": flow["Flow"],
                    "Packet": f'P{flow["Flow"][1:]}_{j+1}',
                    "Arrival": arrival,
                    "Deadline": deadline,
                    "Execution Time": L,
                    "Class": queue_class,
                    "Flow_ID": int(flow["Flow"][1:])
                })

        packet_df = pd.DataFrame(packet_instances)

        queues = {}
        for queue_id in range(1, 9):
            queue_packets = packet_df[packet_df['Class'] == queue_id].copy()
            if not queue_packets.empty:
                queues[queue_id] = queue_packets.sort_values(
                    by=['Arrival', 'Deadline', 'Execution Time', 'Flow_ID'],
                    ascending=[True, True, False, True]
                ).reset_index(drop=True)

        def edf_scheduler_fixed(queues, cipg=96, max_time=None):
            working_queues = {}
            for queue_id in range(1, 8):
                if queue_id in queues:
                    working_queues[queue_id] = queues[queue_id].copy().reset_index(drop=True)

            schedule = []
            t = 0
            if max_time is None:
                max_time = hyperperiod
            packet_count = 0

            while t < max_time:
                all_eligible_packets = []
                for queue_id in range(1, 8):
                    if queue_id in working_queues and len(working_queues[queue_id]) > 0:
                        eligible_packets = working_queues[queue_id][
                            working_queues[queue_id]['Arrival'] <= t
                        ]
                        for idx, packet in eligible_packets.iterrows():
                            all_eligible_packets.append({
                                'queue_id': queue_id,
                                'packet_data': packet,
                                'packet_index': idx,
                                'queue_position': idx
                            })

                if not all_eligible_packets:
                    next_arrivals = []
                    for queue_id in range(1, 8):
                        if queue_id in working_queues and len(working_queues[queue_id]) > 0:
                            remaining = working_queues[queue_id]
                            if not remaining.empty:
                                next_arrival = remaining['Arrival'].min()
                                if next_arrival > t:
                                    next_arrivals.append(next_arrival)
                    if next_arrivals:
                        t = min(next_arrivals)
                    else:
                        break
                    continue

                earliest_deadline_packet = min(all_eligible_packets,
                                               key=lambda x: (x['packet_data']['Deadline'],
                                                              -x['packet_data']['Execution Time'],
                                                              x['packet_data']['Flow_ID']))

                selected_queue_id = earliest_deadline_packet['queue_id']
                selected_position = earliest_deadline_packet['queue_position']

                if selected_position == 0:
                    packet_to_schedule = earliest_deadline_packet
                else:
                    head_packet_data = working_queues[selected_queue_id].iloc[0]
                    packet_to_schedule = {
                        'queue_id': selected_queue_id,
                        'packet_data': head_packet_data,
                        'packet_index': 0,
                        'queue_position': 0
                    }

                packet_data = packet_to_schedule['packet_data']
                queue_id = packet_to_schedule['queue_id']
                gate_open = t
                gate_close = t + packet_data['Execution Time']

                schedule.append({
                    'Packet_ID': packet_data['Packet'],
                    'Flow': packet_data['Flow'],
                    'Queue': queue_id,
                    'Arrival': packet_data['Arrival'],
                    'Deadline': packet_data['Deadline'],
                    'Execution_Time': packet_data['Execution Time'],
                    'Gate_Open': gate_open,
                    'Gate_Close': gate_close,
                    'Schedule_Order': packet_count + 1
                })

                working_queues[queue_id] = working_queues[queue_id].drop(
                    working_queues[queue_id].index[0]
                ).reset_index(drop=True)

                t = gate_close + cipg
                packet_count += 1

                if sum(len(q) for q in working_queues.values()) == 0:
                    break

            return schedule

        schedule = edf_scheduler_fixed(queues, cipg=96, max_time=hyperperiod)
        schedule_df = pd.DataFrame(schedule)

        busy_periods = []
        for _, packet in schedule_df.iterrows():
            busy_periods.append([packet['Gate_Open'], packet['Gate_Close'] + 96])
        busy_periods.sort()

        merged_busy = []
        for start, end in busy_periods:
            if not merged_busy or merged_busy[-1][1] < start:
                merged_busy.append([start, end])
            else:
                merged_busy[-1][1] = max(merged_busy[-1][1], end)

        available_intervals = []
        if merged_busy and merged_busy[0][0] > 0:
            available_intervals.append([0, merged_busy[0][0]])
        for i in range(len(merged_busy) - 1):
            gap_start = merged_busy[i][1]
            gap_end = merged_busy[i + 1][0]
            if gap_end > gap_start:
                available_intervals.append([gap_start, gap_end])
        if merged_busy and merged_busy[-1][1] < hyperperiod:
            available_intervals.append([merged_busy[-1][1], hyperperiod])
        if not merged_busy:
            available_intervals.append([0, hyperperiod])

        scheduled_be_packets = []

        if 8 in queues:
            be_packets = queues[8].copy()
            max_execution_time = packet_df['Execution Time'].max()

            for interval_start, interval_end in available_intervals:
                guard_band_needed = False
                if not schedule_df.empty:
                    before_packets = schedule_df[schedule_df['Gate_Close'] + 96 == interval_start]
                    after_packets = schedule_df[schedule_df['Gate_Open'] == interval_end]
                    if not before_packets.empty and not after_packets.empty:
                        guard_band_needed = True

                guard_band_duration = max_execution_time if guard_band_needed else 0
                packets_in_interval = []
                current_time = interval_start

                remaining_be_packets = be_packets[~be_packets['Packet'].isin(
                    [p['Packet_ID'] for p in scheduled_be_packets]
                )]

                for _, packet in remaining_be_packets.iterrows():
                    packet_id = packet["Packet"]
                    arrival = packet["Arrival"]
                    deadline = packet["Deadline"]
                    exec_time = packet["Execution Time"]

                    gate_open = max(arrival, current_time)
                    gate_close = gate_open + exec_time
                    space_from_start = gate_close - interval_start + 96
                    total_space_with_guard = space_from_start + guard_band_duration

                    if (gate_open >= interval_start and
                        gate_close <= deadline and
                        total_space_with_guard <= (interval_end - interval_start)):

                        packets_in_interval.append({
                            'Packet_ID': packet_id,
                            'Flow': packet['Flow'],
                            'Queue': 8,
                            'Arrival': arrival,
                            'Deadline': deadline,
                            'Execution_Time': exec_time,
                            'Gate_Open': gate_open,
                            'Gate_Close': gate_close,
                            'Interval_Start': interval_start,
                            'Interval_End': interval_end
                        })
                        current_time = gate_close + 96

                for i, packet_entry in enumerate(packets_in_interval):
                    is_last = (i == len(packets_in_interval) - 1)
                    if guard_band_needed and is_last:
                        packet_entry.update({
                            'Guard_Band_Needed': True,
                            'Guard_Band_Duration': guard_band_duration,
                            'Guard_Band_Start': packet_entry['Gate_Close'] + 96,
                            'Guard_Band_End': packet_entry['Gate_Close'] + 96 + guard_band_duration
                        })
                    else:
                        packet_entry.update({
                            'Guard_Band_Needed': False,
                            'Guard_Band_Duration': 0,
                            'Guard_Band_Start': None,
                            'Guard_Band_End': None
                        })
                    scheduled_be_packets.append(packet_entry)

        scheduled_packet_ids = set()
        if not schedule_df.empty:
            scheduled_packet_ids.update(schedule_df['Packet_ID'].tolist())
        if scheduled_be_packets:
            scheduled_packet_ids.update([p['Packet_ID'] for p in scheduled_be_packets])

        queues_1_7_packets = packet_df[packet_df['Class'].isin(range(1, 8))]
        queues_8_packets = packet_df[packet_df['Class'] == 8]

        unscheduled_1_7 = [p for p in queues_1_7_packets['Packet'] if p not in scheduled_packet_ids]
        unscheduled_be = [p for p in queues_8_packets['Packet'] if p not in scheduled_packet_ids]

        deadline_misses = []
        if not schedule_df.empty:
            for _, sp in schedule_df.iterrows():
                if sp['Gate_Close'] > sp['Deadline']:
                    deadline_misses.append(sp['Packet_ID'])

        is_scheduleable = len(unscheduled_1_7) == 0 and len(deadline_misses) == 0

        tt_scheduled = len(queues_1_7_packets) - len(unscheduled_1_7)
        be_scheduled = len(scheduled_be_packets)
        total_scheduled = tt_scheduled + be_scheduled
        total_packets = len(packet_df)
        total_unscheduled = total_packets - total_scheduled

        print(f"\n=== PACKET SCHEDULING SUMMARY ===")
        print(f"Total packets: {total_packets}")
        print(f"Scheduled packets: {total_scheduled}")
        print(f"  - Mandatory packets scheduled: {tt_scheduled}")
        print(f"  - Optional packets scheduled: {be_scheduled}")
        print(f"Unscheduled packets: {total_unscheduled}")
        print(f"  - Mandatory packets unscheduled: {len(unscheduled_1_7)}")
        print(f"  - Optional packets unscheduled: {len(unscheduled_be)}")
        print(f"Deadline violations: {len(deadline_misses)}")

        all_packets = []
        for _, packet in packet_df.iterrows():
            pid = packet['Packet']
            is_scheduled = pid in scheduled_packet_ids
            if is_scheduled:
                if not schedule_df.empty and pid in schedule_df['Packet_ID'].values:
                    sp = schedule_df[schedule_df['Packet_ID'] == pid].iloc[0]
                    missed = sp['Gate_Close'] > sp['Deadline']
                else:
                    missed = False
                status = "Scheduled - Deadline Missed" if missed else "Scheduled - Deadline Met"
            else:
                status = "Unscheduled"

            all_packets.append({
                'Flow': packet['Flow'],
                'Packet': pid,
                'Class': packet['Class'],
                'Status': status
            })

        all_packets_df = pd.DataFrame(all_packets)
        status_counts = all_packets_df['Status'].value_counts()

        print(f"\n=== STATUS BREAKDOWN ===")
        for status, count in status_counts.items():
            print(f"{status}: {count}")
        if len(deadline_misses) == 0:
            print("All scheduled packets meet their deadlines")

        print(f"\n=== SAMPLE OF ALL PACKETS STATUS ===")
        print(all_packets_df.head(10).to_string(index=False))

        if is_scheduleable:
            complete_packets = []
            for _, packet in packet_df.iterrows():
                pid = packet['Packet']
                is_scheduled = pid in scheduled_packet_ids
                info = {
                    'Packet_ID': pid,
                    'Flow': packet['Flow'],
                    'Queue': packet['Class'],
                    'Arrival': packet['Arrival'],
                    'Deadline': packet['Deadline'],
                    'Execution_Time': packet['Execution Time'],
                    'Scheduled': is_scheduled
                }
                if is_scheduled:
                    if not schedule_df.empty and pid in schedule_df['Packet_ID'].values:
                        sp = schedule_df[schedule_df['Packet_ID'] == pid].iloc[0]
                        info.update({
                            'Gate_Open': sp['Gate_Open'],
                            'Gate_Close': sp['Gate_Close'],
                            'Response_Time': sp['Gate_Close'] - packet['Arrival']
                        })
                    else:
                        be = next((p for p in scheduled_be_packets if p['Packet_ID'] == pid), None)
                        if be:
                            info.update({
                                'Gate_Open': be['Gate_Open'],
                                'Gate_Close': be['Gate_Close'],
                                'Response_Time': be['Gate_Close'] - packet['Arrival']
                            })
                else:
                    info.update({'Gate_Open': None, 'Gate_Close': None, 'Response_Time': None})
                complete_packets.append(info)

            complete_df = pd.DataFrame(complete_packets)
            sched = complete_df[complete_df['Scheduled']].sort_values('Gate_Open')
            unsched = complete_df[~complete_df['Scheduled']].sort_values('Arrival')
            complete_df = pd.concat([sched, unsched], ignore_index=True)

            output_csv_path = os.path.join(output_folder, f"all_packet_status_{base_filename}.csv")
            complete_df.to_csv(output_csv_path, index=False)
            print(f"\nResults saved to '{output_csv_path}'")
            return True
        else:
            print("\nQueues 1-7 are UNSCHEDULEABLE. No CSV will be created.")
            return "unschedulable"

    except Exception as e:
        print(f"ERROR processing file {file_path}: {str(e)}")
        return False