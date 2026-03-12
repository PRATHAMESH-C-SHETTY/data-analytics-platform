import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json

PALETTE = ['#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16']

def _layout_dark(height=340):
    return dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sora, sans-serif', color='#94a3b8', size=11),
        margin=dict(l=45, r=20, t=45, b=45),
        height=height,
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0),
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.08)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.08)'),
    )


def _to_json(fig) -> str:
    return json.loads(fig.to_json())


def generate_charts(df: pd.DataFrame) -> list:
    charts = []
    numeric_cols     = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object','category']).columns.tolist()
    datetime_cols    = df.select_dtypes(include='datetime64').columns.tolist()

    # ── 1. Distribution histograms (up to 4 numeric cols)
    for i, col in enumerate(numeric_cols[:4]):
        s = df[col].dropna()
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=s, nbinsx=30, name=col,
            marker=dict(color=PALETTE[i % len(PALETTE)], opacity=0.85,
                        line=dict(width=0.5, color='rgba(255,255,255,0.15)')),
            hovertemplate='%{x}<br>Count: %{y}<extra></extra>'
        ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text=f'Distribution — {col}', font=dict(size=13, color='#e2e8f0')))
        charts.append({'type': 'histogram', 'col': col, 'data': _to_json(fig),
                       'title': f'Distribution: {col}'})

    # ── 2. Box plots comparison (all numeric, max 8)
    if len(numeric_cols) >= 2:
        fig = go.Figure()
        for i, col in enumerate(numeric_cols[:8]):
            s = df[col].dropna()
            mn, mx = s.min(), s.max()
            if mn == mx: continue
            norm = (s - mn) / (mx - mn) * 100
            fig.add_trace(go.Box(
                y=norm, name=col, marker_color=PALETTE[i % len(PALETTE)],
                boxmean='sd', hovertemplate=f'<b>{col}</b><br>Norm. Value: %{{y:.1f}}<extra></extra>'
            ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text='Box Plot Comparison (Normalised)', font=dict(size=13, color='#e2e8f0')))
        charts.append({'type': 'boxplot', 'col': 'all', 'data': _to_json(fig),
                       'title': 'Box Plot Comparison'})

    # ── 3. Bar charts for categorical (top 3 cols)
    for i, col in enumerate(categorical_cols[:3]):
        vc = df[col].value_counts().head(12).reset_index()
        vc.columns = [col, 'count']
        fig = go.Figure(go.Bar(
            x=vc[col].astype(str), y=vc['count'],
            marker=dict(color=PALETTE[i % len(PALETTE)], opacity=0.9,
                        cornerradius=4,
                        line=dict(width=0)),
            text=vc['count'], textposition='outside',
            hovertemplate='%{x}<br>Count: %{y}<extra></extra>'
        ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text=f'Frequency — {col}', font=dict(size=13, color='#e2e8f0')))
        charts.append({'type': 'bar', 'col': col, 'data': _to_json(fig),
                       'title': f'Frequency: {col}'})

    # ── 4. Pie chart for first categorical col
    if categorical_cols:
        col = categorical_cols[0]
        vc  = df[col].value_counts().head(8)
        fig = go.Figure(go.Pie(
            labels=vc.index.astype(str).tolist(),
            values=vc.values.tolist(),
            hole=0.42,
            marker=dict(colors=PALETTE[:len(vc)],
                        line=dict(color='rgba(0,0,0,0.3)', width=2)),
            textinfo='label+percent',
            hovertemplate='%{label}<br>Count: %{value}<br>%{percent}<extra></extra>'
        ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text=f'Proportion — {col}', font=dict(size=13, color='#e2e8f0')))
        charts.append({'type': 'pie', 'col': col, 'data': _to_json(fig),
                       'title': f'Proportion: {col}'})

    # ── 5. Scatter plot
    if len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        sample = df[[x_col, y_col]].dropna().head(600)
        color_col = categorical_cols[0] if categorical_cols and df[categorical_cols[0]].nunique() <= 12 else None
        if color_col:
            cats = df[color_col].dropna().unique()
            fig  = go.Figure()
            for j, cat in enumerate(cats):
                mask = sample.index[df.loc[sample.index, color_col] == cat]
                sub  = sample.loc[mask]
                fig.add_trace(go.Scatter(
                    x=sub[x_col], y=sub[y_col], mode='markers', name=str(cat),
                    marker=dict(color=PALETTE[j % len(PALETTE)], size=6, opacity=0.75)
                ))
        else:
            fig = go.Figure(go.Scatter(
                x=sample[x_col], y=sample[y_col], mode='markers',
                marker=dict(color=PALETTE[0], size=6, opacity=0.7)
            ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text=f'Scatter — {x_col} vs {y_col}', font=dict(size=13, color='#e2e8f0')),
                          xaxis_title=x_col, yaxis_title=y_col)
        charts.append({'type': 'scatter', 'col': f'{x_col}_vs_{y_col}', 'data': _to_json(fig),
                       'title': f'Scatter: {x_col} vs {y_col}'})

    # ── 6. Correlation heatmap
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols[:12]].corr()
        cols = corr.columns.tolist()
        fig  = go.Figure(go.Heatmap(
            z=corr.values, x=cols, y=cols,
            colorscale=[[0,'#ef4444'],[0.5,'#1e293b'],[1,'#6366f1']],
            zmid=0, text=corr.round(2).values,
            texttemplate='%{text}',
            hoverongaps=False,
            hovertemplate='%{y} × %{x}<br>r = %{z:.3f}<extra></extra>'
        ))
        fig.update_layout(**_layout_dark(height=400),
                          title=dict(text='Correlation Heatmap', font=dict(size=13, color='#e2e8f0')))
        charts.append({'type': 'heatmap', 'col': 'correlation', 'data': _to_json(fig),
                       'title': 'Correlation Heatmap'})

    # ── 7. Line / time-series chart
    if datetime_cols and numeric_cols:
        dt_col = datetime_cols[0]
        n_col  = numeric_cols[0]
        ts_df  = df[[dt_col, n_col]].dropna().sort_values(dt_col)
        if len(ts_df) > 500:
            ts_df = ts_df.set_index(dt_col).resample('D').mean().reset_index().dropna()
        fig = go.Figure(go.Scatter(
            x=ts_df[dt_col], y=ts_df[n_col],
            mode='lines', line=dict(color=PALETTE[0], width=2),
            fill='tozeroy', fillcolor='rgba(99,102,241,0.08)',
            hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}<extra></extra>'
        ))
        fig.update_layout(**_layout_dark(),
                          title=dict(text=f'Trend — {n_col} over time', font=dict(size=13, color='#e2e8f0')),
                          xaxis_title=dt_col, yaxis_title=n_col)
        charts.append({'type': 'line', 'col': f'{n_col}_trend', 'data': _to_json(fig),
                       'title': f'Trend: {n_col}'})

    # ── 8. Grouped bar if 2 categorical + 1 numeric
    if len(categorical_cols) >= 2 and numeric_cols:
        cat1, cat2, num = categorical_cols[0], categorical_cols[1], numeric_cols[0]
        if df[cat1].nunique() <= 8 and df[cat2].nunique() <= 6:
            pivot = df.groupby([cat1, cat2])[num].mean().unstack(fill_value=0)
            fig = go.Figure()
            for j, c in enumerate(pivot.columns):
                fig.add_trace(go.Bar(
                    name=str(c), x=pivot.index.astype(str).tolist(),
                    y=pivot[c].tolist(),
                    marker_color=PALETTE[j % len(PALETTE)]
                ))
            fig.update_layout(**_layout_dark(), barmode='group',
                              title=dict(text=f'Grouped — {cat1} × {cat2} (avg {num})',
                                         font=dict(size=13, color='#e2e8f0')))
            charts.append({'type': 'grouped_bar', 'col': f'{cat1}_{cat2}', 'data': _to_json(fig),
                           'title': f'Grouped: {cat1} × {cat2}'})

    return charts
