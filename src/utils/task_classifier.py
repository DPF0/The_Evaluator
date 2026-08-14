"""Task classification based on notebook content analysis."""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class TopicSignature:
    """Signature for identifying a topic in notebook content."""
    topic_key: str
    # Python imports to look for (case-insensitive)
    imports: tuple[str, ...] = ()
    # Function/module patterns in code (case-insensitive)
    code_patterns: tuple[str, ...] = ()
    # Markdown/text keywords (case-insensitive)
    text_keywords: tuple[str, ...] = ()
    # Score weight: higher = stronger match signal
    weight: float = 1.0

    # All known topics, ordered by specificity (most specific first)
    ALL: ClassVar[tuple["TopicSignature", ...]]


# Build after class definition to avoid forward reference issues
_TOPIC_DATA = [
    # NumPy II (must come before NumPy I)
    dict(topic_key="numpy_ii", imports=("numpy", "np"),
         code_patterns=("np.broadcast", "np.vectorize", "np.polynomial",
                        "np.linalg", "np.eig", "np.argsort", "np.argpartition",
                        "np.structured", "np.dtype\\(", "np.fromstring",
                        "np.memmap", "np.outer", "np.inner",
                        "structured array", "broadcasting",
                        "ejercicio 18", "ejercicio 19", "ejercicio 20",
                        "ejercicio 21", "ejercicio 22", "ejercicio 23",
                        "ejercicio 24", "ejercicio 25", "ejercicio 26"),
         text_keywords=("numpy ii", "numpy 2", "numpy2", "numpy_ii"),
         weight=1.0),
    # NumPy I — no ejercicio patterns (shared with NumPy II), rely on filename
    dict(topic_key="numpy_i", imports=("numpy", "np"),
         code_patterns=("np.array", "np.zeros", "np.ones", "np.random",
                        "np.reshape", "np.concatenate", "np.split",
                        "np.hstack", "np.vstack", "np.where", "np.unique",
                        "np.sum", "np.mean", "np.std"),
         text_keywords=("numpy i", "numpy 1", "numpy1", "numpy_i"),
         weight=1.0),
    # Pandas
    dict(topic_key="pandas", imports=("pandas", "pd"),
         code_patterns=("pd.read_csv", "pd.DataFrame", "pd.Series",
                        "pd.merge", "pd.concat", "groupby", ".loc\\[",
                        ".iloc\\[", ".drop", ".pivot", ".melt",
                        "beers", "beer"),
         text_keywords=("pandas", "dataframe", "series"),
         weight=1.0),
    # Matplotlib
    dict(topic_key="matplotlib", imports=("matplotlib", "plt", "pyplot"),
         code_patterns=("plt.plot", "plt.scatter", "plt.bar", "plt.hist",
                        "plt.show", "plt.figure", "plt.subplot",
                        "ax.plot", "ax.scatter", "fig, ax"),
         text_keywords=("matplotlib", "plot", "gráfica", "grafico"),
         weight=1.0),
    # Seaborn
    dict(topic_key="seaborn", imports=("seaborn", "sns"),
         code_patterns=("sns.heatmap", "sns.pairplot", "sns.boxplot",
                        "sns.violinplot", "sns.catplot", "sns.distplot",
                        "sns.jointplot", "sns.relplot", "sns.displot",
                        "sns.set", "sns.pairgrid"),
         text_keywords=("seaborn", "heatmap", "pairplot"),
         weight=1.0),
    # Euro12 / alcohol_consumption
    dict(topic_key="euro12", imports=("pandas", "pd"),
         code_patterns=("euro12", "alcohol_consumption", "alcohol",
                        "Euro12", "Alcohol"),
         text_keywords=("euro12", "euro 12", "alcohol_consumption",
                        "alcohol consumption", "euro"),
         weight=1.0),
    # Occupation / Chipotle
    dict(topic_key="occupation_chipotle", imports=("pandas", "pd"),
         code_patterns=("chipotle", "Chipotle", "occupation", "Occupation"),
         text_keywords=("chipotle", "occupation"),
         weight=1.0),
    # Data Wrangling
    dict(topic_key="data_wrangling", imports=("pandas", "pd"),
         code_patterns=("wrangling", "merge", "concat", "pivot",
                        "stack", "unstack"),
         text_keywords=("data wrangling", "wrangling"),
         weight=1.0),
    # SQL
    dict(topic_key="sql", imports=("sqlite3", "sqlalchemy", "psycopg2"),
         code_patterns=("SELECT", "FROM", "WHERE", "JOIN", "GROUP BY",
                        "CREATE TABLE", "INSERT INTO", "sqlite3", "chinook"),
         text_keywords=("sql", "sqlite", "chinook", "base de datos",
                        "bases de datos"),
         weight=1.0),
    # APIs
    dict(topic_key="apis", imports=("requests", "urllib", "httpx"),
         code_patterns=("requests.get", "requests.post", "api",
                        "json()", ".json()", "API"),
         text_keywords=("api", "apis", "endpoint", "rest"),
         weight=1.0),
    # Files / Downloads
    dict(topic_key="files", imports=("pathlib", "os", "shutil", "zipfile", "csv"),
         code_patterns=("open(", "Path(", "glob(", "shutil", "zipfile", "csv."),
         text_keywords=("archivos", "files", "descargas", "download"),
         weight=1.0),
    # Linear Regression / Advertising
    dict(topic_key="linear_regression", imports=("sklearn", "statsmodels", "scipy"),
         code_patterns=("LinearRegression", "Ridge", "Lasso", "ElasticNet",
                        "train_test_split", "MeanSquaredError",
                        "advertising", "ridge", "lasso", "regularization"),
         text_keywords=("regresión lineal", "linear regression",
                        "advertising", "ridge", "lasso", "regularization"),
         weight=1.0),
    # Logistic Regression
    dict(topic_key="logistic_regression", imports=("sklearn", "statsmodels"),
         code_patterns=("LogisticRegression", "predict-ad-click",
                        "classification_report", "confusion_matrix"),
         text_keywords=("logistic regression", "logística",
                        "predict-ad-click", "clasificación"),
         weight=1.0),
    # Diabetes
    dict(topic_key="diabetes", imports=("sklearn", "pandas"),
         code_patterns=("diabetes", "Diabetes", "load_diabetes"),
         text_keywords=("diabetes"),
         weight=1.0),
    # Decision Trees
    dict(topic_key="decision_trees", imports=("sklearn", "tree", "graphviz"),
         code_patterns=("DecisionTreeClassifier", "DecisionTreeRegressor",
                        "export_text", "export_graphviz"),
         text_keywords=("decision tree", "dtree", "árbol de decisión"),
         weight=1.0),
    # KNN / SVM
    dict(topic_key="knn_svm", imports=("sklearn",),
         code_patterns=("KNeighborsClassifier", "SVC", "SVR",
                        "knn", "svm", "KernelPCA"),
         text_keywords=("knn", "svm", "k-nearest", "soporte vectorial"),
         weight=1.0),
    # Pipelines
    dict(topic_key="pipelines", imports=("sklearn",),
         code_patterns=("Pipeline", "FeatureUnion", "make_pipeline",
                        "ColumnTransformer", "SimpleImputer",
                        "StandardScaler", "OneHotEncoder"),
         text_keywords=("pipeline", "pipelines"),
         weight=1.0),
    # Time Series
    dict(topic_key="time_series", imports=("pandas", "statsmodels", "sklearn"),
         code_patterns=("ARIMA", "SARIMA", "Prophet", "seasonal_decompose",
                        "rolling(", "expanding(", "resample("),
         text_keywords=("time series", "series temporal",
                        "forecast", "predicción"),
         weight=1.0),
    # KMeans / Clustering
    dict(topic_key="kmeans", imports=("sklearn", "matplotlib"),
         code_patterns=("KMeans", "AgglomerativeClustering", "DBSCAN",
                        "fit_predict", "inertia_", "labels_"),
         text_keywords=("kmeans", "clustering", "cluster",
                        "drugs", "drogas"),
         weight=1.0),
    # PCA
    dict(topic_key="pca", imports=("sklearn", "matplotlib"),
         code_patterns=("PCA(", "pca.fit", "pca.transform",
                        "explained_variance_ratio", "components_"),
         text_keywords=("pca", "componentes principales",
                        "principal component"),
         weight=1.0),
    # Regression and Classification (general ML)
    dict(topic_key="regression_classification", imports=("sklearn", "pandas"),
         code_patterns=("accuracy_score", "f1_score", "roc_auc",
                        "cross_val_score", "GridSearchCV"),
         text_keywords=("regresión y clasificación",
                        "regression and classification"),
         weight=1.0),
    # CNN / Deep Learning
    dict(topic_key="cnn", imports=("torch", "tensorflow", "keras", "tf"),
         code_patterns=("Conv2d", "Conv2D", "nn.Conv", "Sequential",
                        "Dense(", "relu", "softmax", "dropout",
                        "clasificador", "paisajes"),
         text_keywords=("red convolucional", "cnn", "deep learning",
                        "clasificador paisajes"),
         weight=1.0),
    # OpenCV
    dict(topic_key="opencv", imports=("cv2", "opencv"),
         code_patterns=("cv2.", "cv2.imread", "cv2.cvtColor",
                        "cv2.detectMultiScale", "cv2.HoughCircle"),
         text_keywords=("opencv", "visión por computador",
                        "computer vision"),
         weight=1.0),
    # NLP / Sarcasm
    dict(topic_key="nlp", imports=("torch", "transformers", "nltk", "spacy"),
         code_patterns=("Tokenizer", "BertModel", "bert-", "roberta",
                        "sarcasm", "Sarcasm"),
         text_keywords=("nlp", "sarcasm", "sarcasmo",
                        "procesamiento lenguaje", "text classification"),
         weight=1.0),
    # Python basics
    dict(topic_key="python_basics",
         code_patterns=("print(", "input(", "range(", "len(",
                        "list(", "dict(", "set(", "tuple("),
         text_keywords=("básico", "basics", "python", "python basics"),
         weight=0.5),
    # Control flow
    dict(topic_key="control_flow",
         code_patterns=("if ", "elif ", "else:", "for ", "while ",
                        "break", "continue"),
         text_keywords=("flujos de control", "control flow",
                        "condicional", "bucle", "loop"),
         weight=0.5),
    # Collections
    dict(topic_key="collections",
         code_patterns=("list(", "dict(", "set(", "tuple(",
                        ".append(", ".extend(", ".pop(", ".remove(",
                        "sorted(", "enumerate(", "zip("),
         text_keywords=("colecciones", "collections", "listas", "diccionarios"),
         weight=0.5),
    # Functions
    dict(topic_key="functions",
         code_patterns=("def ", "lambda ", "return ",
                        "*args", "**kwargs", "yield"),
         text_keywords=("funciones", "functions"),
         weight=0.5),
    # OOP
    dict(topic_key="oop",
         code_patterns=("class ", "__init__", "self.", "super(",
                        "@property", "@staticmethod", "@classmethod"),
         text_keywords=("oop", "orientado a objetos",
                        "object-oriented", "clase", "herencia"),
         weight=0.5),
    # Markdown
    dict(topic_key="markdown",
         text_keywords=("markdown", "ejercicio 1 markdown"),
         weight=0.5),
    # ML Project Idea
    dict(topic_key="ml_project",
         text_keywords=("idea proyecto ml", "ml project idea",
                        "proyecto ml"),
         weight=1.0),
    # DB Project
    dict(topic_key="db_project",
         text_keywords=("proyecto bbdd", "db project",
                        "proyecto base de datos"),
         weight=1.0),
    # Python Exam
    dict(topic_key="python_exam",
         text_keywords=("examen python", "python exam"),
         weight=1.0),
]

TopicSignature.ALL = tuple(TopicSignature(**d) for d in _TOPIC_DATA)


def classify_task(notebook_text: str, filename: str = "") -> str:
    """Classify notebook task based on content analysis.

    Uses a multi-signal scoring system: imports, code patterns, and text
    keywords. Each topic has a signature with weighted signals. Returns the
    topic with the highest score.

    Args:
        notebook_text: Full notebook text (code + markdown).
        filename: Notebook filename (used as additional signal).

    Returns:
        Topic key (e.g., "numpy_i", "pandas").
    """
    text_lower = notebook_text.lower()
    fname_lower = filename.lower().replace("_", " ").replace("-", " ")
    combined = text_lower + " " + fname_lower

    # Fast-path: if filename explicitly matches a topic keyword, return immediately
    for sig in TopicSignature.ALL:
        for kw in sig.text_keywords:
            bounded = rf"\b{re.escape(kw.lower())}\b"
            if re.search(bounded, fname_lower):
                return sig.topic_key

    best_topic = "unknown"
    best_score = 0.0

    for sig in TopicSignature.ALL:
        score = 0.0

        # Import signals (strongest signal)
        for imp in sig.imports:
            pattern = rf"(?:^|[\s;])import\s+{re.escape(imp)}|from\s+{re.escape(imp)}"
            if re.search(pattern, text_lower):
                score += 3.0 * sig.weight

        # Code patterns
        _regex_chars = set(r'\.^$*+?{}[]|()')
        for pat in sig.code_patterns:
            is_plain = not any(c in _regex_chars for c in pat)
            try:
                if is_plain:
                    # Plain string — use word boundaries to prevent substring matches
                    bounded = rf"\b{re.escape(pat)}\b"
                    if re.search(bounded, combined, re.IGNORECASE):
                        score += 1.0 * sig.weight
                else:
                    compiled = re.compile(pat, re.IGNORECASE)
                    if compiled.search(combined):
                        score += 1.0 * sig.weight
            except re.error:
                bounded = rf"\b{re.escape(pat.lower())}\b"
                if re.search(bounded, combined):
                    score += 1.0 * sig.weight

        # Text keywords (word boundaries for all keywords to prevent substring false positives)
        for kw in sig.text_keywords:
            kw_lower = kw.lower()
            bounded = rf"\b{re.escape(kw_lower)}\b"
            if re.search(bounded, combined):
                score += 2.5 * sig.weight

        if score > best_score:
            best_score = score
            best_topic = sig.topic_key

    return best_topic
