"""Generate the ten-page report from actual results and optional deployment evidence.

Run after the full pipeline. Install requirements-docs.txt before running this file.
"""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
for font_name, file_name in [
    ("ReportSans", "DejaVuSans.ttf"),
    ("ReportSans-Bold", "DejaVuSans-Bold.ttf"),
    ("ReportSans-Oblique", "DejaVuSans-Oblique.ttf"),
    ("ReportMono", "DejaVuSansMono.ttf"),
]:
    pdfmetrics.registerFont(TTFont(font_name, str(ROOT / "assets/fonts" / file_name)))
pdfmetrics.registerFontFamily(
    "ReportSans", normal="ReportSans", bold="ReportSans-Bold", italic="ReportSans-Oblique"
)
WIDTH = 504
STYLES = getSampleStyleSheet()
STYLES.add(
    ParagraphStyle(
        "ReportTitle",
        fontName="ReportSans-Bold",
        fontSize=25,
        leading=29,
        textColor=colors.black,
        spaceAfter=16,
    )
)
STYLES.add(
    ParagraphStyle(
        "SectionTitle",
        fontName="ReportSans-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.black,
        spaceAfter=13,
    )
)
STYLES.add(
    ParagraphStyle("ReportBody", fontName="ReportSans", fontSize=10.5, leading=14.2, spaceAfter=8)
)
STYLES.add(
    ParagraphStyle("ReportSmall", fontName="ReportSans", fontSize=8.5, leading=11, spaceAfter=6)
)
STYLES.add(
    ParagraphStyle(
        "ReportCaption",
        fontName="ReportSans-Oblique",
        fontSize=8.3,
        leading=10.5,
        spaceBefore=4,
        spaceAfter=9,
    )
)
STYLES.add(
    ParagraphStyle(
        "ReportSub",
        fontName="ReportSans-Bold",
        fontSize=11.5,
        leading=15,
        spaceBefore=9,
        spaceAfter=6,
    )
)
STYLES.add(
    ParagraphStyle(
        "TableHead", fontName="ReportSans-Bold", fontSize=8.7, leading=11, textColor=colors.white
    )
)
STYLES.add(ParagraphStyle("TableBody", fontName="ReportSans", fontSize=8.7, leading=11))
STYLES.add(ParagraphStyle("Mono", fontName="ReportMono", fontSize=8, leading=10.5, spaceAfter=8))


def p(text, style="ReportBody"):
    return Paragraph(text, STYLES[style])


def table(headers, rows, widths=None):
    cells = [[p(escape(str(v)), "TableHead") for v in headers]]
    cells += [[p(escape(str(v)), "TableBody") for v in row] for row in rows]
    result = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#203c50")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f6")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9d9d9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return result


def fitted_image(path, max_width=WIDTH, max_height=200):
    width, height = ImageReader(str(path)).getSize()
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale, hAlign="CENTER")


def heading(title):
    return p(title, "SectionTitle")


def code(text):
    return Preformatted(text, STYLES["Mono"])


def architecture():
    drawing = Drawing(WIDTH, 225)
    nodes = {
        "raw": (5, 160, 150, ["UCI original file", "checksum and typed CSV"]),
        "train": (175, 160, 150, ["Training split and CV", "242 rows and 12 candidates"]),
        "track": (345, 160, 150, ["MLflow experiment", "parameters metrics artifacts"]),
        "model": (175, 88, 150, ["Selected pipeline", "holdout of 61 and model hash"]),
        "ci": (5, 16, 150, ["GitHub Actions and Docker", "lint test train build smoke"]),
        "serve": (175, 16, 150, ["Docker Desktop Kubernetes", "LoadBalancer and two API pods"]),
        "monitor": (345, 16, 150, ["Prometheus and Grafana", "pod metrics and JSON logs"]),
    }
    for _, (x, y, width, labels) in nodes.items():
        drawing.add(
            Rect(
                x,
                y,
                width,
                47,
                rx=5,
                ry=5,
                fillColor=colors.HexColor("#f2f5f7"),
                strokeColor=colors.HexColor("#9dacb5"),
            )
        )
        for offset, label in enumerate(labels):
            drawing.add(
                String(
                    x + width / 2,
                    y + 28 - offset * 14,
                    label,
                    fontName="ReportSans-Bold" if offset == 0 else "ReportSans",
                    fontSize=8.3 if offset == 0 else 7.8,
                    textAnchor="middle",
                )
            )

    def arrow(x1, y1, x2, y2):
        drawing.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#426276"), strokeWidth=1))
        if x1 == x2:
            drawing.add(
                Polygon(
                    [x2, y2, x2 - 3, y2 + 6, x2 + 3, y2 + 6],
                    fillColor=colors.HexColor("#426276"),
                    strokeColor=None,
                )
            )
        else:
            drawing.add(
                Polygon(
                    [x2, y2, x2 - 6, y2 - 3, x2 - 6, y2 + 3],
                    fillColor=colors.HexColor("#426276"),
                    strokeColor=None,
                )
            )

    arrow(155, 184, 175, 184)
    arrow(325, 184, 345, 184)
    arrow(250, 160, 250, 135)
    arrow(250, 88, 250, 63)
    arrow(155, 40, 175, 40)
    arrow(325, 40, 345, 40)
    drawing.add(String(11, 107, "CI repeats the training and", fontSize=8, fontName="ReportSans"))
    drawing.add(String(11, 95, "container checks on each push", fontSize=8, fontName="ReportSans"))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("ReportSans", 8)
    canvas.setFillColor(colors.HexColor("#52636c"))
    canvas.drawString(54, 29, "AIMLCZG523   MLOps Assignment 1   Heart Risk")
    canvas.drawRightString(558, 29, f"{doc.page} / 10")
    canvas.restoreState()


def build(repository_url="", github_run_url=""):
    report = ROOT / "reports"
    figures = report / "figures"
    metrics = json.loads((report / "metrics.json").read_text())
    data = json.loads((ROOT / "data/processed/data_summary.json").read_text())
    rows = list(csv.DictReader((report / "model_comparison.csv").open(newline="")))
    if metrics["quick_mode"] or metrics["cv_folds"] != 5 or len(rows) != 12:
        raise RuntimeError(
            "Run the full pipeline: the assignment report needs 12 candidates and 5 folds"
        )
    tests_log = (ROOT / "evidence/tests.log").read_text(encoding="utf-8-sig")
    suites = list(ET.parse(ROOT / "evidence/junit.xml").getroot().iter("testsuite"))
    failed = sum(
        int(suite.get("failures", "0")) + int(suite.get("errors", "0")) for suite in suites
    )
    passed = sum(int(suite.get("tests", "0")) - int(suite.get("skipped", "0")) for suite in suites)
    if failed or passed < 22 or f"{passed} passed" not in tests_log:
        raise RuntimeError("The latest unit test execution must pass before building the report")
    coverage = ET.parse(ROOT / "evidence/coverage.xml").getroot()
    total_coverage = float(coverage.get("line-rate"))
    coverage_by_file = {
        Path(item.get("filename")).name: float(item.get("line-rate"))
        for item in coverage.iter("class")
    }
    api = json.loads((ROOT / "evidence/local_api_smoke.json").read_text())
    latency = json.loads((ROOT / "evidence/api_latency.json").read_text())
    test = metrics["test_metrics"]
    screenshots = ROOT / "screenshots"

    def verified(relative, match_model=False):
        path = ROOT / relative
        if not path.exists():
            return False
        result = json.loads(path.read_text(encoding="utf-8-sig"))
        return result.get("passed") is True and (
            not match_model or result.get("model_version") == metrics["model_version"]
        )

    docker_done = verified("evidence/docker_validation.json", match_model=True)
    k8s_done = verified("evidence/kubernetes_validation.json", match_model=True)
    monitoring_done = verified("evidence/monitoring_validation.json")
    status_path = ROOT / "evidence/submission_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8-sig")) if status_path.exists() else {}
    repository_url = repository_url or status.get("repository_url", "")
    github_run_url = github_run_url or status.get("github_run_url", "")
    if k8s_done:
        api = json.loads((ROOT / "evidence/kubernetes_smoke.json").read_text(encoding="utf-8-sig"))
    elif docker_done:
        api = json.loads((ROOT / "evidence/docker_smoke.json").read_text(encoding="utf-8-sig"))
    api_scope = (
        "Kubernetes LoadBalancer" if k8s_done else "isolated Docker" if docker_done else "host"
    )
    repository_text = (
        escape(repository_url) if repository_url else "Add your actual GitHub URL after upload"
    )
    ci_text = (
        escape(github_run_url) if github_run_url else "Hosted workflow execution evidence pending"
    )
    story = []

    # Page 1
    story.extend(
        [
            p("Heart Disease Classification<br/>MLOps Assignment 1", "ReportTitle"),
            p(
                "Machine Learning Operations AIMLCZG523<br/>Prepared for Ameer Basha<br/>11 October 2026",
                "ReportSmall",
            ),
            p(
                "The project implements a reproducible classifier for the UCI Cleveland disease-status "
                "target. Data preparation, feature engineering, model comparison, experiment tracking, "
                "serving, container configuration and local Kubernetes monitoring form one connected pipeline."
            ),
            table(
                ["Measured local result", "Value"],
                [
                    ["Dataset and split", "303 records; 242 train and 61 test"],
                    ["Selected model", "Logistic Regression; C 0.1; threshold 0.5"],
                    [
                        "Holdout accuracy and ROC-AUC",
                        f"{test['accuracy']:.4f} and {test['roc_auc']:.4f}",
                    ],
                    ["Automated tests", f"{passed} passed"],
                ],
                [255, 249],
            ),
            Spacer(1, 10),
            architecture(),
            p(
                "Architecture of the implemented project. Docker, hosted CI and Kubernetes execution "
                "require the laptop or repository run described in the setup guide.",
                "ReportCaption",
            ),
            p(
                "Data, full training, MLflow, tests, the host API and its live monitoring dashboard "
                "were executed during preparation. The final audit tracks container, cluster and "
                "hosted CI evidence separately. The model output classifies the historical dataset; "
                "it is not a validated clinical risk score."
            ),
            p(f"Repository: {repository_text}", "ReportSmall"),
            PageBreak(),
        ]
    )

    # Page 2
    story.extend(
        [
            heading("Dataset acquisition and cleaning"),
            p(
                "The source is the original processed Cleveland file from the UCI Heart Disease archive. "
                "The download script retrieves the archive, extracts the named file and verifies a fixed "
                "SHA-256. The bundled copy permits repeat runs without downloading the data again. "
                "The UCI attribution and CC BY 4.0 licence are retained in the repository [1]."
            ),
            table(
                ["Data contract", "Observed value"],
                [
                    ["Original and clean records", f"{data['raw_rows']} and {data['clean_rows']}"],
                    ["Target mapping", "num 0 becomes 0; num 1 to 4 become 1"],
                    ["Class counts", "164 absent and 139 present"],
                    ["Missing cells", "ca 4; thal 2; all other fields 0"],
                    ["Duplicate rows removed", str(data["duplicates_removed"])],
                ],
                [220, 284],
            ),
            Spacer(1, 9),
            table(
                ["Predictor group", "Fields and original codes"],
                [
                    ["Numerical", "age, trestbps, chol, thalach, oldpeak"],
                    ["Binary categories", "sex, fbs, exang: 0 or 1"],
                    ["Chest pain and ECG", "cp: 1 to 4; restecg: 0 to 2"],
                    ["ST slope and vessels", "slope: 1 to 3; ca: 0 to 3"],
                    ["Thal test", "thal: 3, 6 or 7"],
                ],
                [180, 324],
            ),
            Spacer(1, 9),
            p(
                "Cleaning converts question marks to missing values, validates categories, converts all "
                "fields to numeric types, maps the binary target and removes exact duplicate rows. "
                "No missing target is accepted. No training statistic is learned during this stage. "
                "The cleaned CSV deliberately retains nulls so each CV fold can fit its own imputer."
            ),
            p(
                "The source has 13 predictors and one diagnosis column. Two explicit, label-free "
                "interactions produce 15 modelling predictors before encoding. Additional patient "
                "measurements are not invented to meet a feature-count description."
            ),
            fitted_image(figures / "balance_missing.png", max_height=142),
            p(
                "Observed class balance and missing-value counts from the included data.",
                "ReportCaption",
            ),
            PageBreak(),
        ]
    )

    # Page 3
    story.extend(
        [
            heading("Exploratory data analysis"),
            p(
                "The EDA script produces labelled distributions, class balance, missingness and a "
                "numerical correlation heatmap. It describes the complete dataset; supervised model "
                "selection subsequently uses only the training partition. Category codes are treated "
                "as categories in modelling rather than as continuous clinical measurements."
            ),
            fitted_image(figures / "histograms.png", max_height=233),
            p(
                "Histograms separate disease-status classes while retaining original measurement units.",
                "ReportCaption",
            ),
            fitted_image(figures / "correlation.png", max_height=223),
            p(
                "Pearson associations among numerical fields and the binary target. These associations "
                "describe this cohort and do not establish causal effects.",
                "ReportCaption",
            ),
            p(
                "The maximum achieved heart-rate field tends to associate negatively with the target, "
                "while oldpeak shows a positive association. The modest class imbalance supports "
                "stratified splitting and comparing class-weight choices. The small sample size and "
                "historical hospital cohort restrict the conclusions that can be transferred to new patients."
            ),
            PageBreak(),
        ]
    )

    # Page 4
    comparison = sorted(rows, key=lambda row: float(row["cv_roc_auc_mean"]), reverse=True)
    comparison_rows = []
    for row in comparison:
        params = json.loads(row["parameters"])
        if row["model_family"] == "logistic_regression":
            label = "LR"
            setting = f"C={params['C']}; weight={params['class_weight'] or 'none'}"
        else:
            label = "RF"
            setting = f"depth={params['max_depth'] or 'none'}; leaf={params['min_samples_leaf']}"
        comparison_rows.append(
            [
                label,
                setting,
                f"{float(row['cv_accuracy_mean']):.4f}",
                f"{float(row['cv_roc_auc_mean']):.4f}",
                f"{float(row['cv_roc_auc_std']):.4f}",
            ]
        )
    story.extend(
        [
            heading("Features and model selection"),
            p(
                "FeatureBuilder adds age times oldpeak and exang times oldpeak without using labels. "
                "A ColumnTransformer median-imputes and standardises seven numerical fields, and "
                "mode-imputes and one-hot encodes eight categorical fields. The complete preprocessing "
                "and estimator are serialised as one pipeline, following the training-only fitting "
                "principle that prevents preprocessing leakage [2]."
            ),
            p(
                "Logistic Regression compares C values 0.1, 1 and 10 with either no weighting or balanced "
                "weights. Random Forest uses 150 trees, balanced weights, depths 4, 8 or unlimited, and "
                "minimum leaf sizes 1 or 3. Both use seed 42. Each of the 12 candidates has five "
                "stratified training-only folds, with every preprocessing fit repeated inside the fold."
            ),
            table(
                ["Model", "Configuration", "CV accuracy", "CV AUC", "AUC SD"],
                comparison_rows,
                [56, 206, 87, 78, 77],
            ),
            Spacer(1, 10),
            p(
                "LR means Logistic Regression and RF means Random Forest. Values are fold means; AUC "
                "SD is the sample standard deviation across five folds. Accuracy, precision, recall, "
                "F1, ROC-AUC and Brier score are recorded for all candidates in model_comparison.csv."
            ),
            p(
                "Selection uses the highest mean CV ROC-AUC, not the held-out result or highest CV "
                "accuracy. The selected C=0.1 unweighted LR scored 0.9015 plus or minus 0.0170 AUC "
                "across folds. Differences among the leading settings are small relative to fold "
                "variation; this experiment does not establish a decisive general superiority."
            ),
            PageBreak(),
        ]
    )

    # Page 5
    metric_rows = [[name.replace("_", " ").title(), f"{value:.4f}"] for name, value in test.items()]
    roc = fitted_image(figures / "roc_holdout.png", max_width=246, max_height=183)
    cm = fitted_image(figures / "confusion_matrix.png", max_width=246, max_height=183)
    charts = Table([[roc, cm]], colWidths=[252, 252])
    story.extend(
        [
            heading("Selected model evaluation"),
            p(
                "The selected pipeline is fitted on 242 training records and then evaluated once on "
                "the untouched 61-record holdout. The decision threshold remains 0.5. The held-out set "
                "is not used to choose hyperparameters or to tune the threshold. The same fitted "
                "pipeline is packaged for serving without a later all-data refit."
            ),
            table(["Held-out metric", "Measured value"], metric_rows, [275, 229]),
            Spacer(1, 14),
            charts,
            p("Holdout ROC and confusion matrix for the selected pipeline.", "ReportCaption"),
            p(
                "The confusion matrix contains 29 true negatives, four false positives, two false "
                "negatives and 26 true positives. This gives 55 correct predictions out of 61. "
                "Precision is 26/30 and recall is 26/28. AUC measures ranking over thresholds; the "
                "other classification metrics describe the fixed 0.5 decision threshold."
            ),
            p(
                "The API returns probability_disease and the probability of the chosen class as "
                "confidence. These probabilities have not been separately calibrated. Brier score "
                "is recorded as a probability-error measure, but one small holdout cannot establish "
                "reliable clinical calibration or generalisation. External and subgroup evaluation "
                "would be required before considering use beyond this educational dataset."
            ),
            PageBreak(),
        ]
    )

    # Page 6
    story.extend(
        [
            heading("Experiment tracking with MLflow"),
            p(
                "A full execution creates one comparison parent run and 12 nested candidate runs. "
                "Each candidate records estimator parameters, per-fold metrics, metric means and "
                "standard deviations, its trained pipeline, CV details, an out-of-fold ROC plot and "
                "EDA figures. The parent stores the final holdout metrics, selected pipeline, data "
                "checksum, model metadata and comparison table."
            ),
            table(
                ["Tracking field", "Recorded evidence"],
                [
                    ["Experiment", "HeartRisk-Cleveland"],
                    ["Comparison run", metrics["mlflow_parent_run_id"]],
                    ["Selected candidate run", metrics["selected_run_id"]],
                    [
                        "Backend and artifact store",
                        "Local SQLite database and local artifact directory",
                    ],
                    ["Portable history", "evidence/mlflow_runs.json and mlflow_runs.csv"],
                ],
                [170, 334],
            ),
            Spacer(1, 12),
        ]
    )
    if (screenshots / "local_mlflow_runs.png").exists():
        story.extend(
            [
                fitted_image(screenshots / "local_mlflow_runs.png", max_height=231),
                p(
                    "Genuine browser capture of the executed local MLflow experiment.",
                    "ReportCaption",
                ),
            ]
        )
    story.extend(
        [
            code(
                "mlflow ui --backend-store-uri sqlite:///mlflow.db\n          --host 127.0.0.1 --port 5000"
            ),
            p(
                "Run the command on one line from the project root, then open localhost:5000. "
                "The training and UI processes must point to the same database. Machine-specific "
                "artifact paths are not shipped as a supposedly portable database; training on "
                "the final laptop recreates its live experiment and artifacts. The JSON/CSV export "
                "preserves the preparation run history independently of its absolute paths."
            ),
            PageBreak(),
        ]
    )

    # Page 7
    prediction = api["/predict"]
    story.extend(
        [
            heading("Packaging and API contract"),
            p(
                "The model package contains model.joblib and matching metadata.json. Startup verifies "
                "the saved SHA-256 before loading the model, and missing or inconsistent files fail "
                "readiness. Metadata records the input fields, threshold, split seed, dependency "
                "versions, selected run and results. The API loads the pipeline once and reuses it."
            ),
            table(
                ["Endpoint", "Contract"],
                [
                    ["POST /predict", "13-field JSON patient; class, confidence and model version"],
                    ["POST /predict/batch", "1 to 100 patients; one response per patient"],
                    ["GET /health and /ready", "Liveness and successfully loaded model readiness"],
                    [
                        "GET /dashboard and /monitoring",
                        "Live process dashboard and JSON metric snapshot",
                    ],
                    [
                        "GET /model-info and /metrics",
                        "Model metadata and Prometheus-format measurements",
                    ],
                ],
                [175, 329],
            ),
            Spacer(1, 10),
            code(json.dumps(prediction, indent=2)),
            p(
                f"Actual {api_scope} response for examples/patient.json. Only ca and thal can be explicitly "
                "null; other fields are required and validated. Unknown fields, invalid categories, "
                "non-finite inputs and out-of-range values are rejected. The API accepts the original "
                "Cleveland codes, not the recoded categories used in some third-party CSV files."
            ),
        ]
    )
    image = screenshots / ("kubernetes_prediction.png" if k8s_done else "local_api_prediction.png")
    if image.exists():
        story.extend(
            [
                fitted_image(image, max_height=174),
                p(
                    "Captured Swagger request. Swagger assets are served from the package.",
                    "ReportCaption",
                ),
            ]
        )
    elif api_scope == "host":
        story.extend(
            [
                fitted_image(screenshots / "local_model_info.png", max_height=160),
                p("Executed host metadata endpoint.", "ReportCaption"),
            ]
        )
    story.extend(
        [
            p(
                "requirements.txt includes training/test packages; requirements-serve.txt "
                "keeps the image smaller. Exact direct pins and constraints.txt record the "
                "validated dependency resolution. Host checks used Python 3.12.14; the "
                "Dockerfile uses the supported Python 3.11 family.",
                "ReportSmall",
            ),
            PageBreak(),
        ]
    )

    # Page 8
    story.extend(
        [
            heading("Automated testing and CI workflow"),
            p(
                "GitHub Actions runs on push, pull request or manual dispatch. Its sequential stages "
                "install dependencies, verify data, lint and check formatting, run unit tests, execute "
                "full training, validate the saved model, export MLflow records, build the image and "
                "black-box test its API. Unhandled failures stop the job; an always-run artifact step "
                "preserves available reports, logs, model files and tracking records."
            ),
            table(
                ["Test area", "Behaviour verified"],
                [
                    ["Data", "Checksum, categories, mapping, missing cells and invalid records"],
                    ["Model", "Disjoint splits, fold-local imputation and serialisation parity"],
                    ["API", "Schema errors, nulls, batch limits, metrics and model hash"],
                    [
                        "Deployment contract",
                        "Replica count, ports, probes, LoadBalancer and pod scraping",
                    ],
                ],
                [154, 350],
            ),
            Spacer(1, 10),
            p(
                f"Measured result: {passed} tests passed. Unit coverage is {total_coverage:.0%} overall, "
                f"including {coverage_by_file['api.py']:.0%} of API code and "
                f"{coverage_by_file['features.py']:.0%} of feature code. "
                "The full EDA/training command is a separate "
                "integration execution; the unit coverage figure does not count all of that work. "
                "Actual tests.log, JUnit XML and coverage XML are included."
            ),
            code(
                "ruff check .                         All checks passed\n"
                "ruff format --check .                Formatting passed\n"
                f"pytest                               {passed} passed\n"
                "python scripts/validate_model.py     Package and quality gates passed"
            ),
            p(
                "The educational quality gates require holdout AUC at least 0.75 and accuracy at "
                "least 0.70. A hosted GitHub run additionally proves the isolated container stage. "
                "The workflow prepares a tested artifact; deployment to the laptop cluster is "
                "performed explicitly with deploy.ps1 because a hosted runner cannot directly "
                "reach the user's Docker Desktop context."
            ),
            p(f"GitHub workflow: {ci_text}", "ReportSmall"),
        ]
    )
    if (screenshots / "github_actions.png").exists():
        story.extend(
            [
                fitted_image(screenshots / "github_actions.png", max_height=164),
                p(
                    "User-supplied hosted workflow screenshot; verify the run URL and stages.",
                    "ReportCaption",
                ),
            ]
        )
    else:
        story.append(
            p(
                "Required final evidence: attach the successful Actions run screenshot "
                "from the actual repository. Local pytest output is not hosted CI proof.",
                "ReportSmall",
            )
        )
    story.append(PageBreak())

    # Page 9
    story.extend(
        [
            heading("Docker Desktop Kubernetes deployment"),
            p(
                "The Dockerfile builds a Linux serving image from Python slim, installs serving "
                "dependencies, includes the model and application, and runs as user 10001. A single "
                "Uvicorn worker per container keeps process metrics straightforward. The isolated "
                "smoke script checks the image on port 8001 without mounting the host model directory."
            ),
            table(
                ["Deployment setting", "Configuration"],
                [
                    [
                        "Cluster and namespace",
                        "Docker Desktop context docker-desktop; namespace heartml",
                    ],
                    ["Image and replicas", "heart-risk-api:1.0; two API replicas"],
                    ["Service exposure", "LoadBalancer port 8000 to named container port http"],
                    [
                        "Health and resources",
                        "Startup/readiness /ready; liveness /health; 512 MiB limit",
                    ],
                    ["Pod security", "Non-root; read-only root filesystem; dropped capabilities"],
                ],
                [177, 327],
            ),
            Spacer(1, 10),
            code(
                ".\\scripts\\docker_smoke.ps1\n.\\scripts\\deploy.ps1 -SkipBuild\n"
                "kubectl -n heartml get pods,svc,deploy\n.\\scripts\\collect_evidence.ps1"
            ),
            p(
                "The guide selects a single-node kubeadm cluster when offered. The local manifest "
                "uses imagePullPolicy Never, so the Docker Desktop runtime must see the built image. "
                "If local image visibility differs, the documented fallback publishes to the user's "
                "registry and changes the image name and pull policy together. The cluster remains "
                "Docker Desktop. API access is http://localhost:8000/docs [3, 4]."
            ),
            p(
                f"Container smoke evidence: {'recorded checks passed' if docker_done else 'pending laptop execution'}. "
                f"Kubernetes endpoint evidence: {'recorded checks passed' if k8s_done else 'pending laptop execution'}.",
                "ReportSmall",
            ),
        ]
    )
    for filename, caption in [
        ("docker_build_run.png", "User-supplied isolated Docker build/run evidence."),
        ("kubernetes_resources.png", "User-supplied Docker Desktop pod and Service evidence."),
    ]:
        if (screenshots / filename).exists():
            story.extend(
                [fitted_image(screenshots / filename, max_height=117), p(caption, "ReportCaption")]
            )
    if not k8s_done:
        story.append(
            p(
                "Capture two ready API pods, the LoadBalancer Service and an HTTP 200 "
                "prediction from that Service. The source preparation environment did "
                "not have Docker Desktop; no cluster execution is claimed here. Port "
                "forwarding can diagnose a pod, but does not replace LoadBalancer proof.",
                "ReportSmall",
            )
        )
    story.append(PageBreak())

    # Page 10
    story.extend(
        [
            heading("Monitoring and final evidence"),
            p(
                "Request middleware emits JSON route, status, duration and request-ID logs without "
                "patient payloads. Prometheus discovers each API pod separately using a namespace "
                "Role and ServiceAccount. Grafana provisions its datasource and six-panel dashboard "
                "from ConfigMaps. The traffic script sends valid samples and deliberate HTTP 422 "
                "requests to demonstrate the response-code panel [5, 6]."
            ),
            table(
                ["Measurement", "Meaning"],
                [
                    ["up", "Number of available API pod scrape targets"],
                    ["HTTP request counter", "Response codes and prediction request rate"],
                    ["Duration histogram", "Prediction p95 over a two-minute window"],
                    ["Prediction counter", "Served classes across replicas"],
                    ["Resident memory", "Memory used by each serving process"],
                ],
                [168, 336],
            ),
            Spacer(1, 8),
            p(
                f"Host-only API evidence: 30 sequential HTTP requests, mean latency "
                f"{latency['latency_ms_mean']:.2f} ms and observed p95 {latency['latency_ms_p95']:.2f} ms. "
                "This small local probe is not a container, cluster or capacity benchmark. Live host "
                "metrics are saved in evidence/metrics_sample.txt."
            ),
            p(
                "The built-in /dashboard displays actual request totals, class counts, response codes, "
                "mean latency and a request-rate chart. Its browser capture and JSON snapshot are included. "
                "It observes one serving process; Grafana aggregates the Kubernetes replicas.",
                "ReportSmall",
            ),
        ]
    )
    if (screenshots / "grafana_dashboard.png").exists():
        story.extend(
            [
                fitted_image(screenshots / "grafana_dashboard.png", max_height=149),
                p(
                    "User-supplied running Grafana dashboard after demonstration traffic.",
                    "ReportCaption",
                ),
            ]
        )
    elif (screenshots / "local_api_dashboard.png").exists():
        story.extend(
            [
                fitted_image(screenshots / "local_api_dashboard.png", max_height=139),
                p(
                    "Executed host API monitoring dashboard with real request traffic.",
                    "ReportCaption",
                ),
            ]
        )
    if not monitoring_done:
        story.append(
            p(
                "Run scripts/complete_assignment.ps1 on Docker Desktop to verify container, cluster "
                "and monitoring execution. Collect hosted CI, screenshots and the full video, then "
                "run scripts/finalize_submission.py --strict. The supplied video covers the host pipeline.",
                "ReportSmall",
            )
        )
    story.extend(
        [
            p(
                "The lab uses temporary monitoring storage and local access. Production work would "
                "add persistent volumes, TLS/access control, immutable image releases, external "
                "model validation and labelled-outcome monitoring. Operational metrics alone do "
                "not detect classification accuracy or data drift.",
                "ReportSmall",
            ),
            p("References", "ReportSub"),
            p(
                "[1] UCI Heart Disease dataset. Janosi et al. DOI 10.24432/C52P4X. "
                "archive.ics.uci.edu/dataset/45/heart+disease<br/>"
                "[2] scikit-learn 1.5.2 common pitfalls and pipelines. "
                "scikit-learn.org/1.5/common_pitfalls.html<br/>"
                "[3] Docker Desktop Kubernetes. docs.docker.com/desktop/use-desktop/kubernetes/<br/>"
                "[4] Docker Desktop LoadBalancer exposure. docs.docker.com/compose/bridge/usage/<br/>"
                "[5] Prometheus configuration. prometheus.io/docs/prometheus/latest/configuration/configuration/<br/>"
                "[6] Grafana provisioning. grafana.com/docs/grafana/latest/administration/provisioning/",
                "ReportSmall",
            ),
        ]
    )
    output = ROOT / "docs/MLOps_Assignment_1_Report.pdf"
    output.parent.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=(612, 792),
        rightMargin=54,
        leftMargin=54,
        topMargin=45,
        bottomMargin=47,
        title="Heart Disease MLOps Assignment 1",
        author="Ameer Basha",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    if doc.page != 10:
        raise RuntimeError(f"Report must have exactly 10 pages; produced {doc.page}")
    print(f"Wrote ten-page report: {output}")
    (ROOT / "evidence/report_validation.json").write_text(
        json.dumps(
            {"pages": doc.page, "tests_passed": passed, "model_version": metrics["model_version"]},
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-url", default="")
    parser.add_argument("--github-run-url", default="")
    args = parser.parse_args()
    build(args.repository_url, args.github_run_url)
