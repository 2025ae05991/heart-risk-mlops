"""FastAPI serving with a versioned pipeline, JSON logs, and Prometheus metrics."""

import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

from heartml.settings import FEATURES, MODEL_DIR

logger = logging.getLogger("heartml.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")
HTTP_REQUESTS = Counter(
    "heartml_http_requests_total", "API responses", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "heartml_http_duration_seconds",
    "API request time",
    ["route"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)
PREDICTIONS = Counter("heartml_predictions_total", "Served predictions", ["class_label"])


class Patient(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    age: int = Field(ge=18, le=110)
    sex: Literal[0, 1]
    cp: Literal[1, 2, 3, 4]
    trestbps: float = Field(ge=60, le=250)
    chol: float = Field(ge=50, le=700)
    fbs: Literal[0, 1]
    restecg: Literal[0, 1, 2]
    thalach: float = Field(ge=40, le=250)
    exang: Literal[0, 1]
    oldpeak: float = Field(ge=0, le=10)
    slope: Literal[1, 2, 3]
    ca: Literal[0, 1, 2, 3] | None = Field(...)
    thal: Literal[3, 6, 7] | None = Field(...)


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patients: list[Patient] = Field(min_length=1, max_length=100)


class Prediction(BaseModel):
    prediction: int
    label: str
    confidence: float
    probability_disease: float
    threshold: float
    model_version: str


def create_app(model_path: Path | None = None) -> FastAPI:
    path = model_path or Path(os.environ.get("MODEL_PATH", MODEL_DIR / "model.joblib"))

    @asynccontextmanager
    async def lifespan(application):
        metadata = json.loads(path.with_name("metadata.json").read_text())
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != metadata["model_sha256"]:
            raise RuntimeError("Model checksum differs from metadata; restore both files together.")
        application.state.model = joblib.load(path)
        application.state.metadata = metadata
        application.state.instance = (
            f"{os.environ.get('HOSTNAME', os.environ.get('COMPUTERNAME', 'local'))}:{os.getpid()}"
        )
        logger.info(
            json.dumps({"event": "model_loaded", "model_version": metadata["model_version"]})
        )
        yield

    application = FastAPI(
        title="Heart Risk MLOps API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        description="Original Cleveland codes. Target is dataset disease status.",
    )
    application.mount(
        "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
    )

    @application.get("/docs", include_in_schema=False)
    def docs():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Heart Risk MLOps API",
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
            swagger_favicon_url="/static/favicon-32x32.png",
        )

    @application.middleware("http")
    async def observe(request: Request, call_next):
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            elapsed = time.perf_counter() - started
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_LATENCY.labels(route).observe(elapsed)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "route": route,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 3),
                    }
                )
            )

    def predict_many(patients: list[Patient]):
        if not hasattr(application.state, "model"):
            raise HTTPException(status_code=503, detail="Model is not ready")
        frame = pd.DataFrame([patient.model_dump() for patient in patients], columns=FEATURES)
        frame = frame.astype(float).replace({None: np.nan})
        probabilities = application.state.model.predict_proba(frame)[:, 1]
        metadata = application.state.metadata
        predictions = []
        for probability in probabilities:
            predicted = int(probability >= metadata["threshold"])
            PREDICTIONS.labels(str(predicted)).inc()
            predictions.append(
                Prediction(
                    prediction=predicted,
                    label="disease_present" if predicted else "disease_absent",
                    confidence=float(probability if predicted else 1 - probability),
                    probability_disease=float(probability),
                    threshold=metadata["threshold"],
                    model_version=metadata["model_version"],
                )
            )
        return predictions

    @application.get("/health")
    def health():
        return {"status": "ok"}

    @application.get("/ready")
    def ready():
        if not hasattr(application.state, "model"):
            raise HTTPException(status_code=503, detail="Model is not ready")
        return {"status": "ready", "model_version": application.state.metadata["model_version"]}

    @application.get("/model-info")
    def model_info():
        metadata = application.state.metadata
        return {
            key: metadata[key]
            for key in [
                "model_family",
                "model_version",
                "features",
                "threshold",
                "test_metrics",
                "intended_use",
            ]
        }

    @application.post("/predict", response_model=Prediction)
    def predict(patient: Patient):
        return predict_many([patient])[0]

    @application.post("/predict/batch", response_model=list[Prediction])
    def batch_predict(batch: Batch):
        return predict_many(batch.patients)

    @application.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(content=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})

    @application.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(Path(__file__).parent / "static/dashboard.html")

    @application.get("/monitoring", include_in_schema=False)
    def monitoring():
        samples = [sample for metric in REGISTRY.collect() for sample in metric.samples]
        classes = {"0": 0, "1": 0}
        statuses = {}
        latency_count = latency_seconds = memory = process_started = 0.0
        for sample in samples:
            if sample.name == "heartml_predictions_total":
                classes[sample.labels["class_label"]] = int(sample.value)
            if sample.labels.get("route") in {"/predict", "/predict/batch"}:
                if sample.name == "heartml_http_requests_total":
                    status = sample.labels["status"]
                    statuses[status] = statuses.get(status, 0) + int(sample.value)
                elif sample.name == "heartml_http_duration_seconds_count":
                    latency_count += sample.value
                elif sample.name == "heartml_http_duration_seconds_sum":
                    latency_seconds += sample.value
            if sample.name == "process_resident_memory_bytes":
                memory = sample.value
            elif sample.name == "process_start_time_seconds":
                process_started = sample.value
        ready = hasattr(application.state, "model")
        return {
            "sampled_at": time.time(),
            "instance": application.state.instance,
            "model_ready": ready,
            "model_version": application.state.metadata["model_version"],
            "prediction_count_by_class": classes,
            "prediction_responses_by_status": statuses,
            "prediction_http_requests": sum(statuses.values()),
            "mean_prediction_latency_ms": (
                round(1000 * latency_seconds / latency_count, 3) if latency_count else None
            ),
            "memory_bytes": int(memory) if memory else None,
            "process_uptime_seconds": int(time.time() - process_started)
            if process_started
            else None,
        }

    return application


app = create_app()
