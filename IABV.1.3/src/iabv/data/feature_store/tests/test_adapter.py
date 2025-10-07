# src/iabv/data/feature_store/tests/test_adapter.py
import pytest
try:
    import pandas as pd
except Exception:
    pd = None

from iabv.data.feature_store.adapter import FeatureStoreAdapter

def test_adapter_dataframe_simple():
    if pd is None:
        pytest.skip("pandas required for this test")
    df = pd.DataFrame({
        "price": [10.0, 5.5, 7.0],
        "cat": ["A", "B", "A"]
    })
    adapter = FeatureStoreAdapter()
    feature_list, records, cat_maps = adapter.from_dataframe(df)
    assert isinstance(feature_list, dict)
    assert any(f["name"] == "price" for f in feature_list["features"])
    assert "cat" in cat_maps
    assert len(records) == 3

def test_adapter_csv(tmp_path):
    if pd is None:
        pytest.skip("pandas required for this test")
    p = tmp_path / "sample.csv"
    df = pd.DataFrame({"a":[1,2], "b":["x","y"]})
    df.to_csv(p, index=False)
    adapter = FeatureStoreAdapter()
    fl, recs, maps = adapter.from_csv(str(p))
    assert fl["features"]
    assert len(recs) == 2
