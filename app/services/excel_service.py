import pandas as pd


def read_file(filepath: str) -> pd.DataFrame:
    """Lee un archivo Excel o CSV y retorna un DataFrame."""
    if filepath.lower().endswith(".csv"):
        return pd.read_csv(filepath)
    return pd.read_excel(filepath)


def get_preview(df: pd.DataFrame, rows: int = 100) -> dict:
    """Retorna columnas y filas para la vista previa."""
    return {
        "columns": df.columns.tolist(),
        "rows": df.head(rows).fillna("").values.tolist(),
        "total_rows": len(df),
        "total_cols": len(df.columns),
    }


def get_column_type(df: pd.DataFrame, columna: str) -> str:
    """Retorna 'numeric' o 'categorical' según el tipo de datos."""
    serie = df[columna].dropna()
    if pd.api.types.is_numeric_dtype(serie):
        return "numeric"
    return "categorical"
