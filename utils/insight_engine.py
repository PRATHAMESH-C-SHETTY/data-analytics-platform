import pandas as pd
import numpy as np

def generate_insights(df: pd.DataFrame, stats: dict) -> list:
    insights = []
    numeric    = stats.get('numeric', {})
    categorical= stats.get('categorical', {})
    corr_pairs = stats.get('top_correlations', [])

    # Dataset overview
    nc = len(numeric); cc = len(categorical)
    insights.append({
        'icon': '📊', 'category': 'Overview',
        'severity': 'info',
        'title': 'Dataset Summary',
        'text': (f'Dataset has {len(df):,} rows and {len(df.columns)} columns — '
                 f'{nc} numeric and {cc} categorical. '
                 + (f'No missing values detected.' if df.isnull().sum().sum() == 0
                    else f'{int(df.isnull().sum().sum()):,} missing values found across all columns.'))
    })

    # Per-numeric insights
    for col, s in numeric.items():
        sk = s.get('skewness', 0)
        cv = s.get('cv', 0)
        if abs(sk) > 1.5:
            direction = 'right (positive)' if sk > 0 else 'left (negative)'
            insights.append({
                'icon': '📈', 'category': 'Distribution', 'severity': 'warning',
                'title': f'{col} — Skewed Distribution',
                'text': (f'"{col}" is heavily {direction}-skewed (skewness = {sk:.2f}). '
                         f'This suggests the presence of outliers or a non-normal distribution. '
                         f'Consider log-transformation for modelling.')
            })
        if abs(cv) > 80:
            insights.append({
                'icon': '⚡', 'category': 'Variability', 'severity': 'warning',
                'title': f'{col} — High Variability',
                'text': (f'"{col}" shows very high variability (CV = {cv:.1f}%). '
                         f'Values range from {s["min"]} to {s["max"]} with mean {s["mean"]:.2f}.')
            })
        insights.append({
            'icon': '🔢', 'category': 'Statistics', 'severity': 'info',
            'title': f'{col} — Key Stats',
            'text': (f'Mean: {s["mean"]:.3f} | Median: {s["median"]:.3f} | '
                     f'Std: {s["std"]:.3f} | Range: [{s["min"]}, {s["max"]}].')
        })

    # Categorical insights
    for col, s in categorical.items():
        insights.append({
            'icon': '🏷️', 'category': 'Frequency', 'severity': 'info',
            'title': f'{col} — Top Category',
            'text': (f'"{s["top_value"]}" dominates "{col}" with {s["top_count"]:,} occurrences '
                     f'({s["top_pct"]:.1f}% of all records). '
                     f'{s["unique_count"]} unique categories total.')
        })

    # Correlation insights
    for pair in corr_pairs[:3]:
        c1, c2, r = pair['col1'], pair['col2'], pair['r']
        if abs(r) > 0.6:
            strength = 'very strong' if abs(r) > 0.85 else 'strong'
            direction = 'positive' if r > 0 else 'negative'
            insights.append({
                'icon': '🔗', 'category': 'Correlation', 'severity': 'success',
                'title': f'{c1} ↔ {c2} Correlation',
                'text': (f'{strength.capitalize()} {direction} correlation detected between '
                         f'"{c1}" and "{c2}" (r = {r:.3f}). '
                         + ('They tend to increase together.' if r > 0 else 'They move in opposite directions.'))
            })

    # Missing data
    missing_cols = df.isnull().sum()
    missing_cols = missing_cols[missing_cols > 0]
    if not missing_cols.empty:
        worst = missing_cols.idxmax()
        pct   = round(missing_cols[worst] / len(df) * 100, 1)
        insights.append({
            'icon': '⚠️', 'category': 'Data Quality', 'severity': 'danger',
            'title': 'Missing Values Detected',
            'text': (f'"{worst}" has the highest missing rate ({pct}% missing). '
                     f'Total missing cells: {int(missing_cols.sum()):,}. '
                     f'Missing values were imputed with median/mode for analysis.')
        })

    # Duplicates
    dups = int(df.duplicated().sum())
    if dups > 0:
        insights.append({
            'icon': '♻️', 'category': 'Data Quality', 'severity': 'warning',
            'title': f'{dups:,} Duplicate Rows Removed',
            'text': (f'{dups:,} duplicate rows were detected and removed during cleaning '
                     f'({dups/len(df)*100:.1f}% of original data).')
        })

    return insights[:14]
