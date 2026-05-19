import json, pandas as pd, numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output

master      = pd.read_csv('data/processed/vegshift_master.csv')
koppen      = pd.read_csv('data/processed/koppen_annual.csv')
transitions = json.load(open('data/output/transition_report.json'))
cvle_events = pd.read_json('data/output/crop_viability_events.json')
trend_rep   = pd.read_json('data/output/viability_trend_report.json')
recharge    = json.load(open('data/output/groundwater_recharge_grid.json'))
linkage     = pd.read_json('data/output/transition_cvle_linkage.json')
shap_out    = json.load(open('data/output/shap_explanation.json'))
advisory    = json.load(open('data/output/crop_advisory.json'))
irrigation  = json.load(open('data/output/irrigation_strategy.json'))
eri_report  = json.load(open('data/output/exploitation_risk_report.json'))

CITIES = master['city'].unique().tolist()
CTRL   = ['Pune', 'Kolkata', 'Mumbai']
COLORS = px.colors.qualitative.Set2

app = dash.Dash(__name__)
app.title = "VegShift — Vegetation Viability Monitor"

app.layout = html.Div([
    html.H1("VegShift — Vegetation Viability Loss Monitor",
            style={'fontFamily': 'sans-serif', 'color': '#2c3e50', 'padding': '20px'}),

    dcc.Tabs([

        dcc.Tab(label='Sowing Window Drift', children=[
            html.P("Monsoon onset day-of-year vs optimal sowing window. "
                   "Vertical dashed lines = climate zone transitions.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Dropdown(id='sow-city', options=[{'label': c, 'value': c} for c in CITIES],
                         value='Delhi', clearable=False,
                         style={'width': '300px', 'margin': '10px'}),
            dcc.Graph(id='sow-chart'),
        ]),

        dcc.Tab(label='Dual-Deficit Heatmap', children=[
            html.P("Red = atmospheric water deficit AND groundwater recharge failure same year.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='dd-heatmap'),
        ]),

        dcc.Tab(label='CVLE Timeline', children=[
            html.P("Total Crop Viability Loss Events per city across 2000–2024.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='cvle-bar'),
        ]),

        dcc.Tab(label='Transition → CVLE', children=[
            html.P("Every detected climate zone transition with post-transition CVLE lag "
                   "and statistical significance.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='linkage-table'),
        ]),

        dcc.Tab(label='Recharge Efficiency', children=[
            html.P("Annual groundwater recharge efficiency per city 2000–2022. "
                   "Falling line = aquifer losing ability to recover after monsoon.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Dropdown(id='rech-city', options=[{'label': c, 'value': c} for c in CITIES],
                         value=CITIES[:3], multi=True,
                         style={'width': '500px', 'margin': '10px'}),
            dcc.Graph(id='rech-chart'),
        ]),

        dcc.Tab(label='Koppen Zone History', children=[
            html.P("Climate zone classification per city over 25 years. "
                   "Colour changes = zone transitions.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='koppen-chart'),
        ]),

        dcc.Tab(label='SHAP Importance', children=[
            html.P("Global and per-city SHAP feature importance from the Random Forest baseline.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Dropdown(id='shap-city',
                         options=[{'label': 'Global', 'value': 'global'}] +
                                 [{'label': c, 'value': c} for c in CITIES],
                         value='global', clearable=False,
                         style={'width': '300px', 'margin': '10px'}),
            dcc.Graph(id='shap-chart'),
        ]),

        dcc.Tab(label='Trend Report', children=[
            html.P("25-year linear trend in viability risk probability per city. "
                   "Red = statistically significant deterioration.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='trend-chart'),
        ]),

        dcc.Tab(label='Crop Advisory', children=[
            html.P("Top-ranked crops per city scored on zone fit, temperature, rainfall, "
                   "groundwater stress, and 5-year climate trajectory.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Dropdown(id='adv-city', options=[{'label': c, 'value': c} for c in CITIES],
                         value=CITIES[0], clearable=False,
                         style={'width': '300px', 'margin': '10px'}),
            dcc.Graph(id='adv-chart'),
        ]),

        dcc.Tab(label='Irrigation Strategy', children=[
            html.P("Groundwater stress level and recommended irrigation method per city.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='irr-chart'),
        ]),

        dcc.Tab(label='Exploitation Risk', children=[
            html.P("Exploitation Risk Index (ERI) per city with breakdown of contributing factors. "
                   "Orange bar = alert threshold exceeded.",
                   style={'padding': '10px', 'fontFamily': 'sans-serif'}),
            dcc.Graph(id='eri-chart'),
        ]),

    ])
], style={'fontFamily': 'sans-serif', 'backgroundColor': '#f9f9f9'})


@app.callback(Output('sow-chart', 'figure'), Input('sow-city', 'value'))
def update_sow(city):
    cdf     = master[master['city'] == city].sort_values('year')
    sow_doy = cdf['sow_doy'].iloc[0]
    fig     = go.Figure()

    fig.add_trace(go.Scatter(
        x=cdf['year'], y=cdf['monsoon_onset_doy'],
        mode='lines+markers', name='Monsoon Onset DOY',
        line=dict(color='steelblue', width=2)
    ))

    fig.add_hrect(y0=sow_doy - 14, y1=sow_doy + 14,
                  fillcolor='green', opacity=0.15,
                  annotation_text='Optimal Sowing Window')

    for t in transitions:
        if t['city'] == city:
            fig.add_vline(x=t['transition_year'], line_dash='dash',
                          line_color='red', opacity=0.7,
                          annotation_text=f"{t['from_zone']}→{t['to_zone']}",
                          annotation_position='top right')

    fig.update_layout(title=f'Sowing Window Drift — {city}',
                      xaxis_title='Year', yaxis_title='Day of Year',
                      template='plotly_white')
    return fig


@app.callback(Output('dd-heatmap', 'figure'), Input('dd-heatmap', 'id'))
def update_dd(_):
    pivot = master.pivot_table(
        index='city', columns='year', values='dual_deficit', aggfunc='max'
    ).fillna(0)
    fig = px.imshow(pivot, color_continuous_scale=['white', 'crimson'],
                    labels={'color': 'Dual Deficit'},
                    title='Dual-Deficit Heatmap (1 = atmospheric + groundwater failure)')
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('cvle-bar', 'figure'), Input('cvle-bar', 'id'))
def update_cvle(_):
    counts = master.groupby('city')['cvle_label'].sum().reset_index()
    counts = counts.sort_values('cvle_label', ascending=False)
    counts['color'] = counts['city'].apply(
        lambda c: 'lightgray' if c in CTRL else 'tomato'
    )
    fig = px.bar(counts, x='city', y='cvle_label',
                 color='color', color_discrete_map='identity',
                 title='Total CVLE Events per City (2000–2024)',
                 labels={'cvle_label': 'CVLE Count', 'city': 'City'})
    fig.update_layout(showlegend=False, template='plotly_white')
    return fig


@app.callback(Output('linkage-table', 'figure'), Input('linkage-table', 'id'))
def update_linkage(_):
    if len(linkage) == 0:
        return go.Figure()
    df_l = linkage.copy()
    df_l['significant'] = df_l['significant'].map({True: '✓ Yes', False: '✗ No'})
    df_l['lag_display'] = df_l['post_transition_cvle_lag'].apply(
        lambda x: f"{int(x)} yr" if x is not None and not pd.isna(x) else '—'
    )
    fig = go.Figure(data=[go.Table(
        header=dict(values=['City', 'Year', 'From', 'To', 'Pre Risk',
                            'Post Risk', 'Δ Risk', 'p-value', 'Sig?', 'CVLE Lag'],
                    fill_color='#2c3e50', font=dict(color='white', size=12)),
        cells=dict(values=[
            df_l['city'], df_l['transition_year'],
            df_l['from_zone'], df_l['to_zone'],
            df_l['pre_risk_mean'], df_l['post_risk_mean'],
            df_l['risk_delta'], df_l['p_value'],
            df_l['significant'], df_l['lag_display']
        ], fill_color='lavender', font=dict(size=11))
    )])
    fig.update_layout(title='Transition → CVLE Causal Linkage Table',
                      template='plotly_white')
    return fig


@app.callback(Output('rech-chart', 'figure'), Input('rech-city', 'value'))
def update_rech(cities_sel):
    fig = go.Figure()
    for city in (cities_sel if isinstance(cities_sel, list) else [cities_sel]):
        if city in recharge:
            years = sorted(recharge[city].keys())
            vals  = [recharge[city][y] for y in years]
            fig.add_trace(go.Scatter(
                x=[int(y) for y in years], y=vals,
                mode='lines+markers', name=city
            ))
    fig.update_layout(title='Groundwater Recharge Efficiency (2000–2022)',
                      xaxis_title='Year',
                      yaxis_title='Recharge Efficiency',
                      template='plotly_white')
    return fig


@app.callback(Output('koppen-chart', 'figure'), Input('koppen-chart', 'id'))
def update_koppen(_):
    kdf   = koppen.copy()
    zones = sorted(kdf['koppen_zone'].unique())
    fig   = px.scatter(kdf, x='year', y='city', color='koppen_zone',
                       title='Koppen Zone History per City (2000–2024)',
                       labels={'koppen_zone': 'Zone'},
                       category_orders={'koppen_zone': zones})
    fig.update_traces(marker=dict(size=12, symbol='square'))
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('shap-chart', 'figure'), Input('shap-city', 'value'))
def update_shap(selection):
    if selection == 'global':
        data = pd.DataFrame(shap_out['global_importance'])
        fig  = px.bar(data.sort_values('mean_abs_shap'),
                      x='mean_abs_shap', y='feature', orientation='h',
                      title='Global SHAP Feature Importance',
                      labels={'mean_abs_shap': 'Mean |SHAP|', 'feature': 'Feature'})
    else:
        imp  = shap_out['city_importance'].get(selection, {})
        data = pd.DataFrame({'feature': list(imp.keys()),
                             'mean_abs_shap': list(imp.values())})
        fig  = px.bar(data.sort_values('mean_abs_shap'),
                      x='mean_abs_shap', y='feature', orientation='h',
                      title=f'SHAP Feature Importance — {selection}',
                      labels={'mean_abs_shap': 'Mean |SHAP|', 'feature': 'Feature'})
    fig.update_layout(template='plotly_white')
    return fig


@app.callback(Output('trend-chart', 'figure'), Input('trend-chart', 'id'))
def update_trend(_):
    t = trend_rep.sort_values('slope', ascending=False).copy()
    t['color'] = t.apply(
        lambda r: 'tomato'    if r['trend'] == 'deteriorating'
             else 'steelblue' if r['trend'] == 'improving'
             else 'lightgray', axis=1
    )
    fig = go.Figure()
    for _, row in t.iterrows():
        fig.add_trace(go.Bar(
            x=[row['city']], y=[row['slope']],
            marker_color=row['color'],
            name=row['city'],
            text=f"p={row['p_value']} | {row['trend']}",
            textposition='outside'
        ))
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    fig.update_layout(title='25-Year Viability Risk Trend (slope of linear regression)',
                      xaxis_title='City', yaxis_title='Slope',
                      showlegend=False, template='plotly_white')
    return fig


@app.callback(Output('adv-chart', 'figure'), Input('adv-city', 'value'))
def update_advisory(city):
    data = advisory.get(city, {})
    crops = data.get('ranked_crops', [])
    df_a  = pd.DataFrame(crops)
    df_a['color'] = df_a['zone_match'].map({True: 'steelblue', False: 'lightcoral'})
    fig = go.Figure(go.Bar(
        x=df_a['score'], y=df_a['crop'], orientation='h',
        marker_color=df_a['color'],
        text=df_a['season'], textposition='inside',
    ))
    fig.update_layout(
        title=f'Crop Advisory — {city}  (zone={data.get("current_zone", "")}, '
              f'rain trend={data.get("rain_trend_5yr", 0):+.1f} mm/yr, '
              f'temp trend={data.get("temp_trend_5yr", 0):+.3f} C/yr)',
        xaxis_title='Advisory Score', yaxis_title='Crop',
        xaxis_range=[0, 100], template='plotly_white',
        legend_title='Zone match: blue=yes, red=no',
    )
    return fig


@app.callback(Output('irr-chart', 'figure'), Input('irr-chart', 'id'))
def update_irrigation(_):
    rows = []
    for city, s in irrigation.items():
        rows.append({
            'city':   city,
            'level':  s['rsi_level'],
            'method': s['irrigation_method'],
            'gw_depth': s['gw_depth_mbgl'],
            'rsi':    s['recharge_efficiency'],
        })
    df_i = pd.DataFrame(rows).sort_values('gw_depth', ascending=False)
    color_map = {'critical': 'crimson', 'stressed': 'tomato',
                 'moderate': 'orange',  'healthy':  'steelblue'}
    df_i['color'] = df_i['level'].map(color_map)
    fig = go.Figure(go.Bar(
        x=df_i['city'], y=df_i['gw_depth'],
        marker_color=df_i['color'],
        text=df_i['method'].str.replace('_', ' '),
        textposition='outside',
        customdata=df_i[['level', 'rsi']].values,
        hovertemplate='%{x}<br>Depth: %{y:.1f} mbgl<br>RSI level: %{customdata[0]}<br>'
                      'Recharge eff: %{customdata[1]:.4f}<extra></extra>',
    ))
    fig.add_hline(y=12, line_dash='dash', line_color='orange',
                  annotation_text='Stressed threshold (12 mbgl)')
    fig.add_hline(y=20, line_dash='dash', line_color='crimson',
                  annotation_text='Critical threshold (20 mbgl)')
    fig.update_layout(
        title='Irrigation Strategy — Groundwater Depth & Recommended Method',
        xaxis_title='City', yaxis_title='Pre-monsoon Depth (mbgl)',
        template='plotly_white',
    )
    return fig


@app.callback(Output('eri-chart', 'figure'), Input('eri-chart', 'id'))
def update_eri(_):
    components = ['cvle_prob_5yr', 'drought_risk', 'gw_stress',
                  'trajectory_risk', 'transition_risk']
    comp_labels = ['CVLE Prob', 'Drought', 'GW Stress', 'Trajectory', 'Transition']
    cities_sorted = sorted(eri_report.keys(), key=lambda c: -eri_report[c]['eri'])
    fig = go.Figure()
    palette = px.colors.sequential.Reds[2:]
    for i, (comp, label) in enumerate(zip(components, comp_labels)):
        fig.add_trace(go.Bar(
            name=label,
            x=cities_sorted,
            y=[eri_report[c]['eri_components'][comp] for c in cities_sorted],
            marker_color=palette[i % len(palette)],
        ))
    alert_cities = [c for c in cities_sorted if eri_report[c]['alert']]
    if alert_cities:
        fig.add_hline(y=0.65, line_dash='dash', line_color='red',
                      annotation_text='Alert threshold (ERI=0.65)')
    fig.update_layout(
        barmode='stack',
        title='Exploitation Risk Index (ERI) — Stacked Components',
        xaxis_title='City', yaxis_title='ERI (0–1)',
        template='plotly_white',
    )
    return fig


if __name__ == '__main__':
    app.run(debug=True, port=8050)
