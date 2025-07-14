import re
from datetime import datetime

def parse_timestamps_log(timestamps_log_path):
    with open(timestamps_log_path, 'r') as file:
        lines = file.readlines()
    
    log_intervals = []
    for i in range(0, len(lines), 4):
        log_file = lines[i].strip()
        start_time = datetime.strptime(lines[i+1].strip(), '%Y-%m-%d %H:%M:%S.%f')
        end_time = datetime.strptime(lines[i+2].strip(), '%Y-%m-%d %H:%M:%S.%f')
        throughput = lines[i+3].strip()
        log_intervals.append((log_file, start_time, end_time, throughput))
    
    return log_intervals

def trim_log_file(log_file, start_time, end_time, throughput):
    with open(log_file, 'r') as file:
        lines = file.readlines()
    
    trimmed_lines = [f"Throughput: {throughput}\n"]
    for line in lines:
        match = re.match(r'\[(.*?)\]', line)
        if match:
            timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S.%f')
            if start_time <= timestamp <= end_time:
                trimmed_lines.append(line)
    
    with open(log_file, 'w') as file:
        file.writelines(trimmed_lines)

def trim_logs(timestamps_log_path):
    log_intervals = parse_timestamps_log(timestamps_log_path)
    for log_file, start_time, end_time, throughput in log_intervals:
        trim_log_file(log_file, start_time, end_time, throughput)

# Example usage
trim_logs('logs/timestamps.log')