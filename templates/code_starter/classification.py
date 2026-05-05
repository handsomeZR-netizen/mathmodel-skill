"""
分类类 code starter — 对应论文 §5.x 分类/判别
适用: 二分类 / 多分类 / 不平衡数据

国赛常见: Logistic / SVM / 随机森林 / XGBoost
变体名建议: "Stacking 集成分类模型"
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, StackingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

np.random.seed(42)
Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)


# ============================================================
# 1. 单模型评估
# ============================================================
def evaluate_classifier(model, X_train, X_test, y_train, y_test):
    """
    返回完整指标 + 混淆矩阵
    """
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average='weighted', zero_division=0),
        "recall": recall_score(y_test, y_pred, average='weighted', zero_division=0),
        "f1": f1_score(y_test, y_pred, average='weighted', zero_division=0),
    }

    # AUC (二分类)
    if len(np.unique(y_test)) == 2 and hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)[:, 1]
        metrics["auc"] = roc_auc_score(y_test, y_proba)

    cm = confusion_matrix(y_test, y_pred)
    return {"model": model, "metrics": metrics, "confusion_matrix": cm,
            "y_pred": y_pred}


# ============================================================
# 2. 多模型对比
# ============================================================
def compare_models(X, y, test_size=0.2):
    """
    跑 6 个模型对比, 报告 5 折交叉验证 + 测试集指标
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "Logistic": LogisticRegression(max_iter=1000, random_state=42),
        "SVM-RBF": SVC(kernel='rbf', probability=True, random_state=42),
        "DecisionTree": DecisionTreeClassifier(random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
        "GBDT": GradientBoostingClassifier(random_state=42),
    }

    results = {}
    for name, model in models.items():
        # 5 折 CV
        cv_scores = cross_val_score(model, X_train_s, y_train, cv=5, scoring='f1_weighted')
        # 测试集
        eval_result = evaluate_classifier(model, X_train_s, X_test_s, y_train, y_test)
        eval_result["cv_f1_mean"] = cv_scores.mean()
        eval_result["cv_f1_std"] = cv_scores.std()
        results[name] = eval_result

    return results, scaler


# ============================================================
# 3. Stacking 集成 (winning_patterns §4 命名变体)
# ============================================================
def stacking_classifier(X_train, X_test, y_train, y_test):
    """
    Stacking: RF + SVM + GBDT → Logistic 元学习器
    """
    base_estimators = [
        ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
        ('svm', SVC(kernel='rbf', probability=True, random_state=42)),
        ('gb', GradientBoostingClassifier(random_state=42)),
    ]
    final_estimator = LogisticRegression(random_state=42)
    stack = StackingClassifier(
        estimators=base_estimators,
        final_estimator=final_estimator,
        cv=5,
        n_jobs=1,
    )
    return evaluate_classifier(stack, X_train, X_test, y_train, y_test)


# ============================================================
# 4. 不平衡数据处理 (SMOTE)
# ============================================================
def handle_imbalanced(X, y, method="smote"):
    """
    非常用但偶尔需要; 国赛附件数据有时正负样本比例 1:9
    """
    try:
        from imblearn.over_sampling import SMOTE
        from imblearn.under_sampling import RandomUnderSampler
        if method == "smote":
            sampler = SMOTE(random_state=42)
        elif method == "undersample":
            sampler = RandomUnderSampler(random_state=42)
        X_res, y_res = sampler.fit_resample(X, y)
        return X_res, y_res
    except ImportError:
        print("⚠ imblearn 未安装, 直接返回原数据")
        return X, y


# ============================================================
# 5. 可视化
# ============================================================
def plot_confusion_matrix(cm, class_names=None, title="混淆矩阵"):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names, ax=ax)
    ax.set_xlabel("预测类别")
    ax.set_ylabel("真实类别")
    ax.set_title(title)
    plt.tight_layout()
    return fig


def plot_model_comparison(results):
    """
    柱状图对比多模型 F1
    """
    names = list(results.keys())
    f1s = [results[n]["metrics"]["f1"] for n in names]
    cv_means = [results[n]["cv_f1_mean"] for n in names]
    cv_stds = [results[n]["cv_f1_std"] for n in names]

    x = np.arange(len(names))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width/2, f1s, width, label="测试集 F1", color="steelblue")
    ax.bar(x + width/2, cv_means, width, yerr=cv_stds, label="5 折 CV F1 (均值±std)",
           color="seagreen", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30)
    ax.set_ylabel("F1 (weighted)")
    ax.set_title("分类模型对比")
    ax.legend()
    plt.tight_layout()
    return fig


# ============================================================
# 主流程示例
# ============================================================
if __name__ == "__main__":
    # 模拟二分类数据 (实际从附件读)
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=500, n_features=10, n_informative=5,
                                n_redundant=2, n_classes=2, random_state=42,
                                weights=[0.7, 0.3])  # 不平衡

    # 多模型对比
    results, scaler = compare_models(X, y, test_size=0.2)
    print("=== 各模型对比 ===")
    for name, r in results.items():
        print(f"{name}: F1={r['metrics']['f1']:.3f}, CV_F1={r['cv_f1_mean']:.3f}±{r['cv_f1_std']:.3f}")

    # Stacking
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    stack_result = stacking_classifier(X_train_s, X_test_s, y_train, y_test)
    print(f"\nStacking 集成: F1={stack_result['metrics']['f1']:.3f}")

    # 可视化
    fig = plot_model_comparison(results)
    plt.savefig("figures/classification_comparison.png", dpi=300)
    fig2 = plot_confusion_matrix(stack_result["confusion_matrix"], class_names=["类 0", "类 1"],
                                  title="Stacking 混淆矩阵")
    plt.savefig("figures/classification_stacking_cm.png", dpi=300)
    print("\n图已保存 figures/")
