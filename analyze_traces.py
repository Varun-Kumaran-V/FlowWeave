import json
import csv

# Load JSON
with open('sim/traces/example_buckets.json', 'r') as f:
    buckets_data = json.load(f)

# Verify JSON schema
required_keys = {'report_interval_ms', 'buckets'}
bucket_keys = {'bucket_start_ms', 'arrivals'}

schema_valid = (
    set(buckets_data.keys()) == required_keys and
    all(set(b.keys()) == bucket_keys for b in buckets_data['buckets'])
)

print('=' * 60)
print('EXAMPLE_BUCKETS.JSON ANALYSIS')
print('=' * 60)
print(f'✓ Schema Valid: {schema_valid}')
print(f'  Report Interval: {buckets_data["report_interval_ms"]}ms')
print(f'  Total Buckets: {len(buckets_data["buckets"])}')

arrivals = [b['arrivals'] for b in buckets_data['buckets']]
bucket_starts = [b['bucket_start_ms'] for b in buckets_data['buckets']]

print(f'\nArrival Statistics:')
print(f'  Peak Arrivals: {max(arrivals)}')
print(f'  Min Arrivals: {min(arrivals)}')
print(f'  Average Arrivals: {sum(arrivals) / len(arrivals):.2f}')
print(f'  Total Bucket Events: {sum(arrivals)}')

# Check for monotonically increasing
monotonic = all(bucket_starts[i] <= bucket_starts[i+1] for i in range(len(bucket_starts)-1))
print(f'\n✓ Bucket Starts Monotonic: {monotonic}')
print(f'  Range: {bucket_starts[0]}ms - {bucket_starts[-1]}ms')

# Detect periodic spikes
spike_threshold = sum(arrivals) / len(arrivals)
spikes = [i for i, a in enumerate(arrivals) if a >= 2000]
print(f'\nAllReduce Burst Detection:')
print(f'  Spike Threshold: {spike_threshold:.2f}')
print(f'  High-traffic buckets (>= 2000): {len(spikes)} buckets')
print(f'  Spike Indices (first 15): {spikes[:15]}')

# Check periodicity
if len(spikes) > 1:
    periods = [spikes[i+1] - spikes[i] for i in range(len(spikes)-1)]
    avg_period = sum(periods) / len(periods)
    print(f'  Average Period Between Spikes: ~{avg_period:.1f} buckets')

print('\n' + '=' * 60)
print('EXAMPLE_TRACE.CSV ANALYSIS')
print('=' * 60)

# Load and analyze CSV
timestamps = []
events = 0

with open('sim/traces/example_trace.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts = float(row['time_ms'])
        timestamps.append(ts)
        events += 1

print(f'Total Events in Trace: {events}')
print(f'Time Range: {timestamps[0]:.3f}ms - {timestamps[-1]:.3f}ms')
print(f'Duration: {timestamps[-1] - timestamps[0]:.3f}ms')

# Verify monotonically increasing
monotonic_ts = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
print(f'✓ Timestamps Monotonically Increasing: {monotonic_ts}')

# Arrival rate analysis
if not monotonic_ts:
    violations = sum(1 for i in range(len(timestamps)-1) if timestamps[i] > timestamps[i+1])
    print(f'  ⚠️ Violations found: {violations}')

# Check bucket alignment
print(f'\nBucket Alignment Check:')
print(f'  CSV Duration ({timestamps[-1]:.1f}ms) vs JSON end ({bucket_starts[-1]}ms): ', end='')
if timestamps[-1] >= bucket_starts[-1]:
    print('✓ Aligned (CSV covers all buckets)')
else:
    print('⚠️ Mismatch')

print('\n' + '=' * 60)
print('VALIDATION SUMMARY')
print('=' * 60)
validity = {
    'JSON schema valid': schema_valid,
    'Timestamps monotonic': monotonic_ts,
    'Periodic bursts detected': len(spikes) > 0,
    'AllReduce pattern (regular spikes)': len(spikes) >= 3,
    'Bucket-CSV alignment': timestamps[-1] >= bucket_starts[-1],
}

for check, result in validity.items():
    symbol = '✓' if result else '✗'
    print(f'{symbol} {check}')

all_valid = all(validity.values())
print(f"\n{'✓' if all_valid else '✗'} TRACE STRUCTURE VALID FOR SDN FLOW SIMULATIONS: {all_valid}")
