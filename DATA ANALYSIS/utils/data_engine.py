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


def clean_dataset(df: pd.DataFrame, options=None) -> tuple:
    """
    Enhanced data cleaning with customizable options.
    
    Parameters:
    - df: Input DataFrame
    - options: Dict with cleaning preferences (optional)
    
    Returns:
    - tuple: (cleaned_df, cleaning_report)
    """
    df = df.copy()
    report = {
        'rows_removed': 0,
        'duplicates_removed': 0,
        'missing_before': int(df.isnull().sum().sum()),
        'missing_after': 0,
        'columns_dropped': 0,
        'outliers_clipped': False,
        'text_standardized': False,
        'strategies_used': []
    }
    
    before_rows = len(df)
    
    # 1. Remove duplicates
    df = df.drop_duplicates()
    report['duplicates_removed'] = before_rows - len(df)
    report['rows_removed'] = before_rows - len(df)
    if report['duplicates_removed'] > 0:
        report['strategies_used'].append('Removed duplicate rows')
    
    # Get options or use defaults
    if options is None:
        options = {}
    
    # 2. Handle missing values based on column type
    numeric_strategy = options.get('numeric_strategy', 'median')
    categorical_strategy = options.get('categorical_strategy', 'mode')
    custom_numeric_fill = options.get('custom_numeric_fill', 0)
    custom_categorical_fill = options.get('custom_categorical_fill', 'Unknown')
    
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64, float, int]:
            # Numeric columns
            if numeric_strategy == 'mean':
                df[col] = df[col].fillna(df[col].mean())
                report['strategies_used'].append(f'{col}: filled with mean')
            elif numeric_strategy == 'zero':
                df[col] = df[col].fillna(0)
                report['strategies_used'].append(f'{col}: filled with zero')
            elif numeric_strategy == 'custom':
                df[col] = df[col].fillna(custom_numeric_fill)
                report['strategies_used'].append(f'{col}: filled with custom value')
            else:  # median (default)
                df[col] = df[col].fillna(df[col].median())
                report['strategies_used'].append(f'{col}: filled with median')
                
        elif str(df[col].dtype) == 'object':
            # Categorical columns
            if categorical_strategy == 'custom':
                df[col] = df[col].fillna(custom_categorical_fill)
                report['strategies_used'].append(f'{col}: filled with custom value')
            else:  # mode (default)
                mode = df[col].mode()
                fill_value = mode[0] if not mode.empty else 'Unknown'
                df[col] = df[col].fillna(fill_value)
                report['strategies_used'].append(f'{col}: filled with mode')
    
    # 3. Remove columns with too many missing values
    if options.get('remove_high_missing', False):
        threshold = options.get('missing_threshold', 0.5)
        missing_pct = df.isnull().mean()
        cols_to_drop = missing_pct[missing_pct > threshold].index.tolist()
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
            report['columns_dropped'] = len(cols_to_drop)
            report['strategies_used'].append(f'Dropped {len(cols_to_drop)} columns with >{threshold*100:.0f}% missing values')
    
    # 4. Clip outliers in numeric columns
    if options.get('clip_outliers', False):
        lower_pct = options.get('lower_percentile', 0.01)
        upper_pct = options.get('upper_percentile', 0.99)
        for col in df.select_dtypes(include=[np.number]).columns:
            q_lower = df[col].quantile(lower_pct)
            q_upper = df[col].quantile(upper_pct)
            df[col] = df[col].clip(q_lower, q_upper)
        report['outliers_clipped'] = True
        report['strategies_used'].append(f'Clipped outliers ({lower_pct*100:.0f}th-{upper_pct*100:.0f}th percentile)')
    
    # 5. Standardize text columns
    if options.get('standardize_text', False):
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
        report['text_standardized'] = True
        report['strategies_used'].append('Standardized text (trimmed whitespace, converted to lowercase)')
    
    # 6. Detect datetime columns
    for col in df.select_dtypes(include='object').columns:
        try:
            parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors='coerce')
            if parsed.notna().sum() >= len(df) * 0.7:
                df[col] = parsed
                report['strategies_used'].append(f'Converted {col} to datetime')
        except Exception:
            pass
    
    # Final missing count
    report['missing_after'] = int(df.isnull().sum().sum())
    
    return df, report
