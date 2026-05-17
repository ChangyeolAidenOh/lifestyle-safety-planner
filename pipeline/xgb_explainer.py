"""XGBoost-based safety profile explainer with SHAP.

Trains on district-level safety metrics to learn category weights,
then uses SHAP to explain which categories drive safety levels.

Includes fallback to feature_importances_ when SHAP has version conflicts.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


def build_district_features(datasets):
    """Build feature matrix from district-level safety data."""
    from pipeline.safety_scorer import DISTRICT_CENTROIDS, match_district_in_df

    districts = list(DISTRICT_CENTROIDS.keys())
    rows = []

    for district in districts:
        row = {"district": district}

        df = datasets.get("traffic", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["traffic_accidents"] = matched["accident_count"].sum() if not matched.empty else 0
            row["traffic_deaths"] = matched["death_count"].sum() if not matched.empty and "death_count" in matched.columns else 0

        df = datasets.get("crime", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["crime_occurrence"] = matched["occurrence"].sum() if not matched.empty else 0

        df = datasets.get("air_quality", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["pm25_avg"] = matched["pm25"].mean() if not matched.empty else 0

        df = datasets.get("medical_access", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["medical_count"] = len(matched)

        df = datasets.get("flood", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["flood_records"] = len(matched)

        df = datasets.get("fire", pd.DataFrame())
        if not df.empty:
            matched = match_district_in_df(df, district)
            row["fire_count"] = matched["fire_count"].sum() if not matched.empty else 0

        rows.append(row)

    return pd.DataFrame(rows).set_index("district").fillna(0)


def create_composite_label(features_df):
    """Create composite safety label from normalized features."""
    df = features_df.copy()
    for col in df.columns:
        col_min, col_max = df[col].min(), df[col].max()
        if col_max > col_min:
            df[col] = (df[col] - col_min) / (col_max - col_min)
        else:
            df[col] = 0
    if "medical_count" in df.columns:
        df["medical_count"] = 1 - df["medical_count"]
    return df.mean(axis=1).values


def train_explainer(datasets):
    """Train XGBoost model and return SHAP explainer with fallback."""
    if not HAS_XGB:
        return None, None, None

    features_df = build_district_features(datasets)
    if features_df.empty or len(features_df) < 5:
        return None, None, None

    y = create_composite_label(features_df)
    X = features_df

    model = xgb.XGBRegressor(
        n_estimators=50, max_depth=3,
        learning_rate=0.1, random_state=42, base_score=0.5,
    )
    model.fit(X, y)

    explainer = None
    if HAS_SHAP:
        # Approach 1: TreeExplainer with booster
        try:
            booster = model.get_booster()
            explainer = shap.TreeExplainer(booster)
            logger.info("SHAP: TreeExplainer(booster) OK")
        except Exception as e1:
            logger.warning("TreeExplainer failed: %s", e1)
            # Approach 2: Explainer with predict callable
            try:
                explainer = shap.Explainer(model.predict, X)
                logger.info("SHAP: Explainer(predict) OK")
            except Exception as e2:
                logger.warning("Explainer(predict) failed: %s", e2)
                explainer = None

    logger.info("XGBoost trained: %d districts, %d features. SHAP=%s",
                len(X), len(X.columns), explainer is not None)

    return model, explainer, features_df


def explain_district(district_name, model, explainer, features_df):
    """Generate SHAP explanation with fallback to feature_importances_."""
    if model is None or district_name not in features_df.index:
        return None

    row = features_df.loc[[district_name]]
    prediction = float(model.predict(row)[0])
    n_features = len(features_df.columns)

    feature_labels = {
        "traffic_accidents": "교통사고",
        "traffic_deaths": "교통사망",
        "crime_occurrence": "범죄발생",
        "pm25_avg": "PM2.5",
        "medical_count": "의료기관",
        "flood_records": "침수이력",
        "fire_count": "화재",
    }

    shap_list = None
    base_val = 0.0

    if explainer is not None:
        try:
            sv = explainer(row)
            sv_array = np.array(sv.values).flatten()[:n_features]
            shap_list = [float(v) for v in sv_array]
            ev = sv.base_values
            base_val = float(np.array(ev).flatten()[0]) if hasattr(ev, '__len__') else float(ev)
        except Exception:
            try:
                sv = explainer.shap_values(row)
                sv_array = np.array(sv).flatten()[:n_features]
                shap_list = [float(v) for v in sv_array]
                ev = explainer.expected_value
                base_val = float(np.array(ev).flatten()[0]) if hasattr(ev, '__len__') else float(ev)
            except Exception as e:
                logger.warning("SHAP extraction failed: %s", e)
                shap_list = None

    if shap_list is None:
        # Fallback: feature_importances_ x normalized feature values
        importances = model.feature_importances_
        row_vals = np.array(row.values[0], dtype=float)
        row_max = row_vals.max()
        if row_max > 0:
            row_norm = row_vals / row_max
        else:
            row_norm = row_vals
        shap_list = [float(imp * val) for imp, val in zip(importances, row_norm)]
        base_val = float(prediction - sum(shap_list))

    return {
        "shap_values": shap_list,
        "feature_names": [feature_labels.get(f, f) for f in features_df.columns],
        "feature_names_raw": list(features_df.columns),
        "feature_values": [float(v) for v in row.values[0]],
        "base_value": base_val,
        "prediction": prediction,
    }


def get_shap_bar_data(explanation):
    """Convert explanation to sorted bar chart data."""
    if explanation is None:
        return []
    pairs = list(zip(explanation["feature_names"], explanation["shap_values"]))
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    return pairs
