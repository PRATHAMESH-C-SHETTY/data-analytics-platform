import pandas as pd
import numpy as np

def run_analysis(df: pd.DataFrame) -> dict:
    numeric_cols     = df.select_dtypes(include=np.number).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object','category']).columns.tolist()
    datetime_cols    = df.select_dtypes(include='datetime64').columns.tolist()

    stats = {
        'column_types': {
            'numeric': numeric_cols,
            'categorical': categorical_cols,
            'datetime': datetime_cols,
        },
        'numeric': {},
        'categorical': {},
        'datetime': {},
    }

    # Numeric
    for col in numeric_cols:
        s = df[col].dropna()
        if s.empty: continue
        stats['numeric'][col] = {
            'mean':     _r(s.mean()),
            'median':   _r(s.median()),
            'std':      _r(s.std()),
            'min':      _r(s.min()),
            'max':      _r(s.max()),
            'q25':      _r(s.quantile(0.25)),
            'q75':      _r(s.quantile(0.75)),
            'skewness': _r(s.skew()),
            'kurtosis': _r(s.kurtosis()),
            'count':    int(s.count()),
            'sum':      _r(s.sum()),
            'cv':       _r(s.std() / s.mean() * 100) if s.mean() != 0 else 0,
        }

    # Categorical
    for col in categorical_cols:
        vc = df[col].value_counts()
        if vc.empty: continue
        stats['categorical'][col] = {
            'unique_count': int(df[col].nunique()),
            'top_value':    str(vc.index[0]),
            'top_count':    int(vc.iloc[0]),
            'top_pct':      _r(vc.iloc[0] / len(df) * 100),
            'top_10':       {str(k): int(v) for k, v in vc.head(10).items()},
        }

    # Datetime
    for col in datetime_cols:
        s = df[col].dropna()
        if s.empty: continue
        stats['datetime'][col] = {
            'min':        str(s.min()),
            'max':        str(s.max()),
            'range_days': int((s.max() - s.min()).days),
        }

    # Correlation matrix
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr().round(3)
        stats['correlation'] = corr.to_dict()
        # Top pairs
        pairs = []
        cols = numeric_cols
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                val = corr.loc[cols[i], cols[j]]
                if not np.isnan(val):
                    pairs.append((cols[i], cols[j], float(val)))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        stats['top_correlations'] = [
            {'col1': a, 'col2': b, 'r': round(r, 3)}
            for a, b, r in pairs[:5]
        ]

    return stats


def _r(v, d=4):
    try:
        if np.isnan(v) or np.isinf(v): return 0
        return round(float(v), d)
    except Exception:
        return 0
