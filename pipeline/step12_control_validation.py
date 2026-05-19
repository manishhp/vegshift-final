import json, pandas as pd

CONTROL_CITIES = ['Pune', 'Kolkata', 'Mumbai']
AT_RISK_CITIES = ['Delhi', 'Jaipur', 'Ahmedabad', 'Lucknow',
                  'Hyderabad', 'Chennai', 'Bangalore']

trend_report   = pd.read_json('data/output/viability_trend_report.json')
transition_rep = json.load(open('data/output/transition_report.json'))
cvle_events    = pd.read_json('data/output/crop_viability_events.json')

print("=" * 60)
print("CONTROL CITY VALIDATION")
print("=" * 60)

ctrl_trends = trend_report[trend_report['city'].isin(CONTROL_CITIES)]
print("\n[1] Trend check (expected: stable)")
print(ctrl_trends[['city', 'slope', 'p_value', 'trend']].to_string(index=False))
failed_trend = ctrl_trends[ctrl_trends['trend'] != 'stable']
if len(failed_trend) > 0:
    print(f"\nWARNING: {list(failed_trend['city'])} show non-stable trends -- check model.")
else:
    print("OK: All control cities show stable viability trends.")

ctrl_cvle = cvle_events[cvle_events['city'].isin(CONTROL_CITIES)]
print(f"\n[2] CVLE count in control cities (expected: 0): {len(ctrl_cvle)}")
if len(ctrl_cvle) > 0:
    print(f"WARNING: Control cities flagged for CVLEs: {ctrl_cvle[['city','year']].values}")
else:
    print("OK: No CVLE events in control cities.")

ctrl_transitions = [t for t in transition_rep if t['city'] in CONTROL_CITIES]
print(f"\n[3] Transitions in control cities (expected: 0): {len(ctrl_transitions)}")
if ctrl_transitions:
    print(f"WARNING: {ctrl_transitions}")
else:
    print("OK: No climate zone transitions in control cities.")

print("\n[4] At-risk city summary:")
for city in AT_RISK_CITIES:
    n_trans = len([t for t in transition_rep if t['city'] == city])
    n_cvle  = len(cvle_events[cvle_events['city'] == city])
    slope   = trend_report[trend_report['city'] == city]['slope'].values[0]
    print(f"  {city:<12} transitions={n_trans}  CVLEs={n_cvle}  slope={slope:+.6f}")

print("\nControl validation complete.")
