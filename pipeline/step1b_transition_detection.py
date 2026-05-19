# pipeline/step1b_transition_detection.py
import pandas as pd, json

koppen = pd.read_csv('data/processed/koppen_annual.csv').sort_values(['city','year'])

PERSISTENCE = 3   # new zone must persist 3+ years

transitions = []

for city, cdf in koppen.groupby('city'):
    cdf   = cdf.sort_values('year').reset_index(drop=True)
    zones = cdf['koppen_zone'].tolist()
    years = cdf['year'].tolist()

    i = 0
    while i < len(zones) - 1:
        if zones[i] != zones[i+1]:
            end_chk = min(i + 1 + PERSISTENCE, len(zones))
            future  = zones[i+1:end_chk]
            if all(z == zones[i+1] for z in future):
                transitions.append({
                    'city':             city,
                    'transition_year':  years[i+1],
                    'from_zone':        zones[i],
                    'to_zone':          zones[i+1],
                    'years_confirmed':  len(future)
                })
                i += PERSISTENCE
            else:
                i += 1
        else:
            i += 1

json.dump(transitions, open('data/output/transition_report.json','w'), indent=2)

print(f"\nTransitions detected: {len(transitions)}")
for t in transitions:
    print(f"  {t['city']} {t['transition_year']}: "
          f"{t['from_zone']} -> {t['to_zone']} "
          f"(confirmed {t['years_confirmed']} yrs)")
