"""
预测类 code starter — 对应论文 §5.x 时序预测 / 回归
适用: 回归 / ARIMA / 灰色预测 GM(1,1) / LSTM / 组合预测

国赛加分: 单一模型 + 组合预测 (e.g., ARIMA + GM(1,1) + 加权)
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import statsmodels.api as sm
import matplotlib.pyplot as plt
from pathlib import Path

np.random.seed(42)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 线性 / Ridge / RF 回归
# ============================================================
def fit_regression(X_train, y_train, X_test, y_test, model_type="linear"):
    """
    Args:
        model_type: "linear" / "ridge" / "rf"
    """
    if model_type == "linear":
        model = LinearRegression()
    elif model_type == "ridge":
        model = Ridge(alpha=1.0)
    elif model_type == "rf":
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    else:
        raise ValueError(model_type)

    model.fit(X_train, y_train)
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    return {
        "model": model,
        "metrics_train": {
            "MAE": mean_absolute_error(y_train, y_pred_train),
            "RMSE": np.sqrt(mean_squared_error(y_train, y_pred_train)),
            "R2": r2_score(y_train, y_pred_train),
        },
        "metrics_test": {
            "MAE": mean_absolute_error(y_test, y_pred_test),
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred_test)),
            "R2": r2_score(y_test, y_pred_test),
        },
        "y_pred_test": y_pred_test,
    }


# ============================================================
# 2. ARIMA 时间序列
# ============================================================
def fit_arima(y, order=(1, 1, 1), forecast_steps=12):
    """
    自动适配 ARIMA(p, d, q)
    建议先用 statsmodels.tsa.stattools.adfuller 检验平稳性
    """
    model = sm.tsa.ARIMA(y, order=order).fit()
    forecast = model.forecast(steps=forecast_steps)
    return {
        "model": model,
        "forecast": forecast,
        "aic": model.aic,
        "bic": model.bic,
        "summary": model.summary(),
    }


# ============================================================
# 3. 灰色预测 GM(1,1)  ⭐ 国赛常用 (小样本)
# ============================================================
def gm11(y, predict_steps=5):
    """
    残差修正 GM(1,1) (winning_patterns §4 命名变体)

    Args:
        y: ndarray (n,) 原始时序
        predict_steps: int 预测步数

    Returns:
        dict with keys: predicted, residual_corrected, params
    """
    n = len(y)
    # 1. 累加生成
    y_cum = np.cumsum(y)
    # 2. 构造 Z 序列 (邻均值)
    z = (y_cum[:-1] + y_cum[1:]) / 2.0
    # 3. 最小二乘求 a, b
    B = np.column_stack([-z, np.ones(n - 1)])
    Y = y[1:]
    a, b = np.linalg.lstsq(B, Y, rcond=None)[0]
    # 4. 预测
    n_total = n + predict_steps
    y_cum_pred = np.zeros(n_total)
    y_cum_pred[0] = y[0]
    for k in range(1, n_total):
        y_cum_pred[k] = (y[0] - b/a) * np.exp(-a * k) + b/a
    # 5. 还原
    y_pred = np.diff(np.concatenate([[0], y_cum_pred]))
    # 6. 残差修正 (在原始数据范围内)
    residuals = y - y_pred[:n]
    # 简单常数修正
    correction = residuals.mean()
    y_pred_corrected = y_pred + correction
    return {
        "predicted": y_pred_corrected,
        "residual": residuals,
        "params": {"a": a, "b": b},
        "in_sample_mape": np.mean(np.abs(residuals / y)) * 100,
    }


# ============================================================
# 4. 组合预测 (加权)  ⭐ 一等奖加分
# ============================================================
def ensemble_prediction(predictions_dict, weights=None):
    """
    Args:
        predictions_dict: {"arima": np.array, "gm11": np.array, "rf": np.array}
        weights: dict 同名 keys, 不传则用误差倒数法估算
    """
    if weights is None:
        # 假设有 in-sample 误差信息可用; 这里简化为均匀权重
        weights = {k: 1.0 / len(predictions_dict) for k in predictions_dict}

    # 标准化权重
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    # 加权
    ensemble = sum(w * predictions_dict[k] for k, w in weights.items())
    return {"ensemble": ensemble, "weights": weights}


# ============================================================
# 5. 残差诊断
# ============================================================
def residual_diagnostics(y_true, y_pred):
    """
    计算多个指标 + 可视化残差
    """
    residuals = y_true - y_pred
    metrics = {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAPE": np.mean(np.abs(residuals / np.maximum(np.abs(y_true), 1e-9))) * 100,
        "R2": r2_score(y_true, y_pred),
        "DurbinWatson": sm.stats.durbin_watson(residuals),
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].plot(y_true, label="真实", marker='o')
    axes[0].plot(y_pred, label="预测", marker='x')
    axes[0].legend()
    axes[0].set_title("预测 vs 真实")
    axes[1].plot(residuals, marker='.')
    axes[1].axhline(0, color='red', ls='--')
    axes[1].set_title("残差时序")
    axes[2].hist(residuals, bins=20)
    axes[2].set_title("残差直方图")
    plt.tight_layout()
    return metrics, fig


# ============================================================
# 主流程示例 (对应论文 §5.x)
# ============================================================
if __name__ == "__main__":
    # 模拟时序数据 (实际从附件读)
    n = 60
    t = np.arange(n)
    y = 10 + 0.5 * t + 5 * np.sin(t * 2 * np.pi / 12) + np.random.normal(0, 1, n)

    # 1. ARIMA 预测
    arima_result = fit_arima(y[:48], order=(2, 1, 1), forecast_steps=12)
    print(f"ARIMA AIC: {arima_result['aic']:.2f}")

    # 2. GM(1,1) 预测
    gm_result = gm11(y[:48], predict_steps=12)
    print(f"GM(1,1) 样本内 MAPE: {gm_result['in_sample_mape']:.2f}%")

    # 3. 组合预测
    pred_arima = arima_result["forecast"]
    pred_gm = gm_result["predicted"][48:60]
    ensemble = ensemble_prediction(
        {"arima": pred_arima, "gm11": pred_gm},
        weights={"arima": 0.6, "gm11": 0.4}
    )

    # 4. 评估
    metrics, fig = residual_diagnostics(y[48:], ensemble["ensemble"])
    print(f"组合预测指标: {metrics}")

    plt.savefig("figures/prediction_diagnostics.png", dpi=300)
    print("已保存 figures/prediction_diagnostics.png")
