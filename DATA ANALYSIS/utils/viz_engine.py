import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json

PALETTE = [
    '#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444',
    '#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16'
]


def _layout_dark(height=340):
    return dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Sora, sans-serif', color='#94a3b8', size=11),
        margin=dict(l=45, r=20, t=45, b=45),
        height=height,
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0),
        xaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.08)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.08)')
    )


def _to_json(fig):
    return json.loads(fig.to_json())


def generate_charts(df: pd.DataFrame):

    charts = []

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object','category']).columns.tolist()
    datetime_cols = df.select_dtypes(include='datetime64').columns.tolist()

    # ---------------------------------------------------
    # 1. Histogram Distribution
    # ---------------------------------------------------

    for i, col in enumerate(numeric_cols[:4]):

        s = df[col].dropna()

        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=s,
                nbinsx=30,
                name=col,
                marker=dict(
                    color=PALETTE[i % len(PALETTE)],
                    opacity=0.85,
                    line=dict(width=0.5, color='rgba(255,255,255,0.15)')
                ),
                hovertemplate='%{x}<br>Count: %{y}<extra></extra>'
            )
        )

        fig.update_layout(
            **_layout_dark(),
            title=dict(text=f'Distribution — {col}', font=dict(size=13, color='#e2e8f0'))
        )

        charts.append({
            "type":"histogram",
            "col":col,
            "data":_to_json(fig),
            "title":f"Distribution: {col}"
        })


    # ---------------------------------------------------
    # 2. Box Plot Comparison
    # ---------------------------------------------------

    if len(numeric_cols) >= 2:

        fig = go.Figure()

        for i, col in enumerate(numeric_cols[:8]):

            s = df[col].dropna()

            mn, mx = s.min(), s.max()

            if mn == mx:
                continue

            norm = (s - mn) / (mx - mn) * 100

            fig.add_trace(
                go.Box(
                    y=norm,
                    name=col,
                    marker_color=PALETTE[i % len(PALETTE)],
                    boxmean='sd'
                )
            )

        fig.update_layout(
            **_layout_dark(),
            title=dict(text="Box Plot Comparison (Normalised)", font=dict(size=13, color='#e2e8f0'))
        )

        charts.append({
            "type":"boxplot",
            "col":"all",
            "data":_to_json(fig),
            "title":"Box Plot Comparison"
        })


    # ---------------------------------------------------
    # 3. Bar Chart (Categorical Frequency)
    # ---------------------------------------------------

    for i, col in enumerate(categorical_cols[:3]):

        vc = df[col].value_counts().head(12).reset_index()
    vc.columns = [col, "count"]

    fig = go.Figure(
        go.Bar(
            x=vc[col].astype(str),
            y=vc["count"],
            marker=dict(
                color=PALETTE[i % len(PALETTE)],
                opacity=0.9,
                line=dict(width=0)
            ),
            text=vc["count"],
            textposition="outside",
            hovertemplate="%{x}<br>Count: %{y}<extra></extra>"
        )
    )

    fig.update_layout(
        **_layout_dark(),
        title=dict(text=f"Frequency — {col}", font=dict(size=13, color="#e2e8f0"))
    )

    charts.append({
        "type": "bar",
        "col": col,
        "data": _to_json(fig),
        "title": f"Frequency: {col}"
    })
    # ---------------------------------------------------
    # 4. Pie Chart
    # ---------------------------------------------------

    if categorical_cols:

        col = categorical_cols[0]
        vc = df[col].value_counts().head(8)

        fig = go.Figure(
            go.Pie(
                labels=vc.index.astype(str),
                values=vc.values,
                hole=0.42,
                marker=dict(
                    colors=PALETTE[:len(vc)],
                    line=dict(color='rgba(0,0,0,0.3)', width=2)
                ),
                textinfo="label+percent"
            )
        )

        fig.update_layout(
            **_layout_dark(),
            title=dict(text=f"Proportion — {col}", font=dict(size=13, color="#e2e8f0"))
        )

        charts.append({
            "type":"pie",
            "col":col,
            "data":_to_json(fig),
            "title":f"Proportion: {col}"
        })


    # ---------------------------------------------------
    # 5. Scatter Plot
    # ---------------------------------------------------

    if len(numeric_cols) >= 2:

        x_col = numeric_cols[0]
        y_col = numeric_cols[1]

        sample = df[[x_col,y_col]].dropna().head(600)

        fig = go.Figure(
            go.Scatter(
                x=sample[x_col],
                y=sample[y_col],
                mode="markers",
                marker=dict(
                    color=PALETTE[0],
                    size=6,
                    opacity=0.7
                )
            )
        )

        fig.update_layout(
            **_layout_dark(),
            title=dict(text=f"Scatter — {x_col} vs {y_col}", font=dict(size=13,color="#e2e8f0")),
            xaxis_title=x_col,
            yaxis_title=y_col
        )

        charts.append({
            "type":"scatter",
            "col":f"{x_col}_vs_{y_col}",
            "data":_to_json(fig),
            "title":f"Scatter: {x_col} vs {y_col}"
        })


    # ---------------------------------------------------
    # 6. Correlation Heatmap
    # ---------------------------------------------------

    if len(numeric_cols) >= 2:

        corr = df[numeric_cols[:12]].corr()

        fig = go.Figure(
            go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale=[[0,'#ef4444'],[0.5,'#1e293b'],[1,'#6366f1']],
                zmid=0
            )
        )

        fig.update_layout(
            **_layout_dark(height=400),
            title=dict(text="Correlation Heatmap", font=dict(size=13,color="#e2e8f0"))
        )

        charts.append({
            "type":"heatmap",
            "col":"correlation",
            "data":_to_json(fig),
            "title":"Correlation Heatmap"
        })


    return charts