# src/iabv/data/feature_store/adapter.py
"""
FeatureStoreAdapter
- Convierte pandas.DataFrame / CSV / Parquet -> FeatureList dict + records iterable
- Construye category_mappings (dict: feature_name -> {cat_value: int})
- Normaliza valores (casts simples) y prepara registros para validate_records
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# imports opcionales
try:
    import pandas as pd  # type: ignore
    _HAS_PANDAS = True
except Exception:
    pd = None  # type: ignore
    _HAS_PANDAS = False

# intentar reusar FeatureList/FeatureSpec si existen
try:
    from .feature_list import FeatureList  # type: ignore
except Exception:
    FeatureList = None  # type: ignore

try:
    from .feature_spec import FeatureSpec  # type: ignore
except Exception:
    FeatureSpec = None  # type: ignore

# helper: detecta tipo simple y shape
def infer_feature_from_series(name: str, s) -> Dict[str, Any]:
    """
    Infers a feature spec dict from a pandas Series (or a list-like).
    Returns {'name': name, 'type': 'numeric'|'categorical'|'vector', 'shape': n, 'required': True}
    """
    # default
    f = {"name": name, "required": True, "meta": {}}

    # Si pandas no está disponible o la serie no es Series, usar heurística simple
    if not _HAS_PANDAS:
        # intentar simple: numbers => numeric scalar
        sample = None
        try:
            sample = next(iter(s))
        except Exception:
            sample = s
        if isinstance(sample, (int, float, bool)):
            f.update({"type": "numeric", "shape": 1})
        elif isinstance(sample, (list, tuple)):
            try:
                shape = len(sample)
                f.update({"type": "numeric", "shape": int(shape)})
            except Exception:
                f.update({"type": "numeric", "shape": 1})
        else:
            f.update({"type": "categorical", "shape": 1})
        return f

    # con pandas: series.dtypes
    dtype = getattr(s, "dtype", None)
    if pd.api.types.is_numeric_dtype(dtype):
        # ¿vector? comprobar si los elementos son listas/arrays
        if s.apply(lambda x: hasattr(x, "__iter__") and not isinstance(x, (str, bytes))).any():
            # tomar primer no-nulo iterable para shape
            for x in s:
                if x is not None and x is not pd.NA:
                    if hasattr(x, "__len__") and not isinstance(x, (str, bytes)):
                        try:
                            f.update({"type": "numeric", "shape": int(len(x))})
                            break
                        except Exception:
                            pass
            else:
                f.update({"type": "numeric", "shape": 1})
        else:
            f.update({"type": "numeric", "shape": 1})
    elif pd.api.types.is_bool_dtype(dtype):
        f.update({"type": "numeric", "shape": 1})
    else:
        # tratar como categórica por defecto
        # si es object y contiene lists -> vector
        if s.apply(lambda x: hasattr(x, "__iter__") and not isinstance(x, (str, bytes))).any():
            # vector of unknown type -> treat numeric vector
            for x in s:
                if x is not None and x is not pd.NA and hasattr(x, "__len__") and not isinstance(x, (str, bytes)):
                    try:
                        f.update({"type": "numeric", "shape": int(len(x))})
                        break
                    except Exception:
                        pass
            else:
                f.update({"type": "categorical", "shape": 1})
        else:
            f.update({"type": "categorical", "shape": 1})
    return f

def build_category_mapping_for_series(s, max_categories: int = 10000) -> Optional[Dict[Any, int]]:
    """Return mapping if series is categorical-like (strings/objects) and distinct values are reasonable."""
    if not _HAS_PANDAS:
        return None
    try:
        nunique = int(s.nunique(dropna=True))
        if nunique > max_categories:
            return None
        cats = pd.Series(s.dropna().unique()).tolist()
        mapping = {v: i for i, v in enumerate(sorted(cats, key=lambda x: str(x)))}
        return mapping
    except Exception:
        return None

class FeatureStoreAdapter:
    def __init__(self, infer_categorical_mapping: bool = True, max_categories: int = 10000):
        self.infer_categorical_mapping = infer_categorical_mapping
        self.max_categories = max_categories

    def from_dataframe(self, df) -> Tuple[Dict[str, Any], Iterable[Dict[str, Any]], Dict[str, Dict[Any,int]]]:
        """
        Dado un pandas.DataFrame (o equivalente), infiere un feature_list dict,
        devuelve (feature_list_dict, records_iterable, category_mappings).
        - feature_list_dict: {'feature_list_id': 'auto', 'features': [ ... ]}
        - records_iterable: generator/ list of row dicts
        - category_mappings: {feature_name: {category_value: int}}
        """
        if not _HAS_PANDAS:
            raise RuntimeError("pandas is required for from_dataframe")

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        features: List[Dict[str, Any]] = []
        cat_maps: Dict[str, Dict[Any,int]] = {}

        for col in df.columns:
            spec = infer_feature_from_series(col, df[col])
            # si es categórica y debemos inferir mapping -> construir mapping
            if spec["type"] in ("categorical", "category") and self.infer_categorical_mapping:
                mapping = build_category_mapping_for_series(df[col], max_categories=self.max_categories)
                if mapping:
                    cat_maps[col] = mapping
                    # set shape = len(mapping) as cardinality
                    spec["shape"] = len(mapping)
            features.append(spec)

        feature_list = {"feature_list_id": "auto", "features": features}

        # prepare records: convert categories to mapping indices if mapping exists
        def records_gen():
            for _, row in df.iterrows():
                rec = {}
                for col in df.columns:
                    v = row[col]
                    if pd.isna(v):
                        rec[col] = None
                        continue
                    if col in cat_maps:
                        # map value -> index, if not found, keep original (validator will catch)
                        rec[col] = cat_maps[col].get(v, v)
                    else:
                        rec[col] = v
                yield rec

        return feature_list, list(records_gen()), cat_maps

    def from_csv(self, path: str, **pd_read_kwargs):
        if not _HAS_PANDAS:
            raise RuntimeError("pandas required for from_csv")
        df = pd.read_csv(path, **pd_read_kwargs)
        return self.from_dataframe(df)

    def from_parquet(self, path: str, **pd_read_kwargs):
        if not _HAS_PANDAS:
            raise RuntimeError("pandas required for from_parquet")
        df = pd.read_parquet(path, **pd_read_kwargs)
        return self.from_dataframe(df)

    def validate_and_prepare(self, feature_list_payload: Dict[str, Any], records: Iterable[Dict[str, Any]],
                             category_mappings: Optional[Dict[str, Dict[Any,int]]] = None):
        """
        Llama a FeatureValidator si está disponible para validar spec y registros.
        Retorna (report_spec, report_records, prepared_records)
        - report_spec: salida de validate()
        - report_records: salida de validate_records()
        - prepared_records: lista de records procesados (por ahora es el mismo records)
        """
        # validación si existe FeatureValidator
        try:
            from .validator import FeatureValidator, validate_feature_list_payload  # type: ignore
        except Exception:
            FeatureValidator = None
            validate_feature_list_payload = None

        spec_report = None
        if validate_feature_list_payload is not None:
            try:
                # validate_feature_list_payload puede lanzar o devolver (según impl.)
                validate_feature_list_payload(feature_list_payload)
                spec_report = {"valid": True, "errors": []}
            except Exception as e:
                spec_report = {"valid": False, "errors": [str(e)]}
        else:
            spec_report = {"valid": True, "errors": []}

        records_report = None
        prepared = list(records)
        if FeatureValidator is not None:
            try:
                fl_obj = feature_list_payload
                # si existe FeatureList clase, intentar from_dict
                if FeatureList is not None and hasattr(FeatureList, "from_dict"):
                    try:
                        fl_obj = FeatureList.from_dict(feature_list_payload)
                    except Exception:
                        fl_obj = feature_list_payload
                fv = FeatureValidator(fl_obj, category_mappings=category_mappings or {})
                records_report = fv.validate_records(prepared)
            except Exception as e:
                records_report = {"valid": False, "errors": [str(e)]}
        else:
            records_report = {"valid": True, "errors": []}

        return spec_report, records_report, prepared
