import pandas as pd
import numpy as np
import json

ALLOWED_EXT = {'csv', 'xlsx', 'xls', 'json'}

def load_dataset(filepath: str, ext: str) -> pd.DataFrame:
    ext = ext.lower().strip('.')
    if ext == 'csv':
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                df = pd.read_csv(filepath, encoding=enc, low_memory=False)
                return df
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file.")
    elif ext in ('xlsx', 'xls'):
        return pd.read_excel(filepath)
    elif ext == 'json':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try records, columns, or wrap dict
            if any(isinstance(v, list) for v in data.values()):
                return pd.DataFrame(data)
            return pd.DataFrame([data])
        raise ValueError("Unsupported JSON structure.")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def inspect_dataset(df: pd.DataFrame) -> dict:
    info = {
        'shape': {'rows': len(df), 'cols': len(df.columns)},
        'columns': [],
        'missing_total': int(df.isnull().sum().sum()),
        'missing_pct': round(df.isnull().mean().mean() * 100, 2),
        'duplicate_rows': int(df.duplicated().sum()),
        'memory_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 3),
        'numeric_count': int(df.select_dtypes(include=np.number).shape[1]),
        'categorical_count': int(df.select_dtypes(include=['object','category']).shape[1]),
        'datetime_count': int(df.select_dtypes(include='datetime64').shape[1]),
    }
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        if 'int' in dtype_str or 'float' in dtype_str:
            kind = 'numeric'
        elif 'datetime' in dtype_str:
            kind = 'datetime'
        else:
            kind = 'categorical'
        sample_val = df[col].dropna().iloc[0] if df[col].dropna().shape[0] > 0 else 'N/A'
        info['columns'].append({
            'name': col,
            'dtype': dtype_str,
            'kind': kind,
            'missing': int(df[col].isnull().sum()),
            'missing_pct': round(df[col].isnull().mean() * 100, 1),
            'unique': int(df[col].nunique()),
            'sample': str(sample_val)[:50],
        })
    return info


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    before = len(df)
    df = df.drop_duplicates()

    # Try to detect datetime columns from object columns
    for col in df.select_dtypes(include='object').columns:
        try:
            parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors='coerce')
            if parsed.notna().sum() >= len(df) * 0.7:
                df[col] = parsed
        except Exception:
            pass

    # Fill missing values
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64, float, int]:
            df[col] = df[col].fillna(df[col].median())
        elif str(df[col].dtype) == 'object':
            mode = df[col].mode()
            df[col] = df[col].fillna(mode[0] if not mode.empty else 'Unknown')

    return df
