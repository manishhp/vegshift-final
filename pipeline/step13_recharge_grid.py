import json, pandas as pd

df   = pd.read_csv('data/processed/vegshift_master.csv')
grid = {
    city: dict(zip(
        cdf.sort_values('year')['year'].astype(str),
        cdf.sort_values('year')['recharge_efficiency'].round(4)
    ))
    for city, cdf in df.groupby('city')
}
json.dump(grid, open('data/output/groundwater_recharge_grid.json', 'w'), indent=2)
print("Recharge grid saved -- 10 cities x 25 years")
