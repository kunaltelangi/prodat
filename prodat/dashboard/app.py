import os
import shutil
import uuid
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from flask import Flask, url_for, render_template, request, jsonify, abort

import plotly

from prodat.config import Config
from prodat.core.entity.run import Run
from prodat.core.controller.base import BaseController
from prodat.core.util.misc_functions import prettify_datetime, printable_object

# Attempt to import prodat_monitoring from common possible locations.
# If unavailable, set to None and handle gracefully at runtime.
prodat_monitoring = None
try:
    import prodat_monitoring  # type: ignore
except Exception:
    try:
        from prodat import monitoring as prodat_monitoring  # type: ignore
    except Exception:
        prodat_monitoring = None

app = Flask(__name__)
base_controller = BaseController()

user = {
    "name": "Shabaz Patel",
    "username": "shabazp",
    "email": "shabaz@prodat.com",
    "gravatar_url": "https://www.gravatar.com/avatar/"
    + str(uuid.uuid1())
    + "?s=220&d=identicon&r=PG",
}


def _get_model_dict() -> Dict[str, Any]:
    """Return model dict or abort 404 if model missing."""
    if not getattr(base_controller, "model", None):
        abort(404, description="No model available")
    return base_controller.model.__dict__


def _safe_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _ensure_monitoring():
    if prodat_monitoring is None:
        abort(500, description="prodat_monitoring is not available/importable")


def _process_deployment_info(deployment_info: Dict[str, Any], model_version_id: str, deployment_version_id: str) -> Dict[str, Any]:
    deployment_info = dict(deployment_info)  # copy to avoid mutating original
    # Prettify created_at if present
    if "created_at" in deployment_info and deployment_info["created_at"] is not None:
        try:
            deployment_info["created_at"] = prettify_datetime(deployment_info["created_at"])
        except Exception:
            # leave as-is if prettify fails
            pass

    # Filter endpoints/service_paths to only include those matching model_version_id
    mv_key = "".join(str(model_version_id).split("_"))
    if "endpoints" in deployment_info and isinstance(deployment_info["endpoints"], list):
        deployment_info["endpoints"] = [ep for ep in deployment_info["endpoints"] if mv_key in ep]
    if "service_paths" in deployment_info and isinstance(deployment_info["service_paths"], list):
        deployment_info["service_paths"] = [p for p in deployment_info["service_paths"] if mv_key in p]

    deployment_info["deployment_version_id"] = deployment_version_id
    deployment_info["model_version_id"] = model_version_id
    return deployment_info


@app.route("/")
def home():
    models = [base_controller.model.__dict__] if getattr(base_controller, "model", None) else []
    return render_template("profile.html", user=user, models=models)


@app.route("/<model_name>")
def model_summary(model_name: str):
    model = _get_model_dict()
    # static example snapshots left intact as sample data
    snapshots = [
        {
            "id": "alfwokd",
            "created_at": "Sun March 3rd, 2018",
            "labels": ["cool", "default"],
            "config": {"algorithm": "random forest"},
            "stats": {"accuracy": 0.98},
        }
    ]
    config_keys = ["algorithm"]
    stats_keys = ["accuracy"]
    return render_template(
        "model_summary.html",
        user=user,
        model=model,
        snapshots=snapshots,
        config_keys=config_keys,
        stats_keys=stats_keys,
    )


@app.route("/<model_name>/experiments")
def model_experiments(model_name: str):
    model = _get_model_dict()
    experiments: List[Run] = []
    if model_name == model.get("name"):
        tasks = base_controller.dal.task.query({"model_id": model["id"]})
        experiments = [Run(task) for task in tasks]
        for experiment in experiments:
            experiment.config_printable = printable_object(experiment.config)
            experiment.start_time_prettified = prettify_datetime(experiment.start_time)
            experiment.end_time_prettified = prettify_datetime(experiment.end_time)
            experiment.results_printable = printable_object(experiment.results)
    return render_template("model_experiments.html", user=user, model=model, experiments=experiments)


@app.route("/<model_name>/snapshots")
def model_snapshots(model_name: str):
    model = _get_model_dict()
    snapshots: List[Any] = []
    if model_name == model.get("name"):
        snaps = base_controller.dal.snapshot.query({"model_id": model["id"]})
        snapshots = [(snapshot, snapshot.to_dictionary(stringify=True)) for snapshot in snaps]

    # Safely compute config_keys and stats_keys even if snapshots empty
    config_keys = set()
    stats_keys = set()
    for snapshot, _ in snapshots:
        cfg = getattr(snapshot, "config", {}) or {}
        st = getattr(snapshot, "stats", {}) or {}
        config_keys.update(cfg.keys())
        stats_keys.update(st.keys())

    return render_template(
        "model_snapshots.html",
        user=user,
        model=model,
        snapshots=snapshots,
        config_keys=config_keys,
        stats_keys=stats_keys,
    )


@app.route("/data/<model_name>/deployments/<deployment_version_id>/<model_version_id>")
def model_deployment_data(model_name: str, deployment_version_id: str, model_version_id: str):
    _ensure_monitoring()

    start = _safe_int(request.args.get("start"), 0) or 0
    count = _safe_int(request.args.get("count"), None)
    data_type = request.args.get("data_type", None)
    key_name = request.args.get("key_name", None)
    graph_type = request.args.get("graph_type", None)

    if not data_type and not key_name and not graph_type:
        return "error", 400

    query_filter = {
        "model_id": model_name,
        "deployment_version_id": deployment_version_id,
        "model_version_id": model_version_id,
        "start": int(start),
    }
    if count is not None:
        query_filter["count"] = int(count)

    new_data = prodat_monitoring.search_metadata(query_filter)

    num_new_results = len(new_data or [])

    if data_type not in ["input", "prediction", "feedback", "system_metrics"]:
        return "error", 400

    graph_data_output: Dict[str, Any] = {}

    if graph_type == "timeseries":
        new_time_data = []
        for datum in new_data:
            t = datum.get("updated_at") or datum.get("created_at")
            if t is None:
                continue
            try:
                # timestamps expected in milliseconds
                new_time_data.append(float(t))
            except Exception:
                continue

        new_time_data_datetime = [
            datetime.fromtimestamp(t / 1000.0).strftime("%Y-%m-%d %H:%M:%S") for t in new_time_data
        ]

        new_feature_data = [datum.get(data_type, {}).get(key_name) if datum.get(data_type) else None for datum in new_data]
        graph_data_output = {"new_data": {"x": [new_time_data_datetime], "y": [new_feature_data]}}

    elif graph_type == "histogram":
        query_filter = {
            "model_id": model_name,
            "deployment_version_id": deployment_version_id,
            "model_version_id": model_version_id,
        }
        cumulative_data = prodat_monitoring.search_metadata(query_filter) or []
        cumulative_feature_data = [
            datum[data_type][key_name]
            for datum in cumulative_data
            if datum.get(data_type) and key_name in datum.get(data_type, {})
        ]

        import numpy as np

        # np.histogram works with empty arrays: it will return empty counts and bins
        counts, binedges = np.histogram(cumulative_feature_data)
        if len(binedges) > 1:
            binsize = binedges[1] - binedges[0]
        else:
            binsize = 0
        bin_names = [
            f"{round(float(binedge), 2)} : {round(float(binedge) + binsize, 2)}" for binedge in binedges
        ]
        graph_data_output = {"cumulative_data": {"x": [bin_names], "y": [counts.tolist()]}}

    elif graph_type == "gauge":
        new_feature_data = [datum.get(data_type, {}).get(key_name) if datum.get(data_type) else None for datum in new_data]
        numeric_values = [v for v in new_feature_data if isinstance(v, (int, float))]
        average = float(sum(numeric_values)) / len(numeric_values) if numeric_values else None
        graph_data_output = {"average": average}

    else:
        return "error", 400

    graph_data_outputJSON = json.dumps(graph_data_output, cls=plotly.utils.PlotlyJSONEncoder)

    return jsonify(graph_data_output_json_str=graph_data_outputJSON, num_new_results=num_new_results)


@app.route("/<model_name>/deployments/<deployment_version_id>/<model_version_id>")
def model_deployment_detail(model_name: str, deployment_version_id: str, model_version_id: str):
    _ensure_monitoring()
    model = _get_model_dict()

    query_filter = {
        "model_id": model_name,
        "model_version_id": model_version_id,
        "deployment_version_id": deployment_version_id,
    }

    input_keys: List[str] = []
    prediction_keys: List[str] = []
    feedback_keys: List[str] = []

    data = prodat_monitoring.search_metadata(query_filter) or []

    if data:
        max_index = 0
        for ind, datum in enumerate(data):
            if datum.get("feedback") is not None:
                max_index = ind
        datum = data[max_index]
        input_keys = list(datum.get("input", {}).keys())
        prediction_keys = list(datum.get("prediction", {}).keys())
        feedback_keys = list(datum.get("feedback", {}).keys()) if datum.get("feedback") is not None else []

    # Determine the graph directory path and create if not present
    graph_dirpath = Path(base_controller.home) / Config().prodat_directory_name / "deployments" / deployment_version_id / model_version_id / "graphs"
    graph_dirpath.mkdir(parents=True, exist_ok=True)

    # Include deployment info
    deployment_info = prodat_monitoring.get_deployment_info(deployment_version_id=deployment_version_id)
    deployment_info = _process_deployment_info(deployment_info, model_version_id, deployment_version_id)

    return render_template(
        "model_deployment_detail.html",
        user=user,
        model=model,
        deployment=deployment_info,
        graph_dirpath=str(graph_dirpath),
        input_keys=input_keys,
        prediction_keys=prediction_keys,
        feedback_keys=feedback_keys,
    )


@app.route("/<model_name>/deployments")
def model_deployments(model_name: str):
    _ensure_monitoring()
    model = _get_model_dict()

    all_data = prodat_monitoring.search_metadata({"model_id": model_name}) or []
    model_version_ids = set(item.get("model_version_id") for item in all_data if item.get("model_version_id") is not None)
    deployment_version_ids = set(item.get("deployment_version_id") for item in all_data if item.get("deployment_version_id") is not None)

    deployments: List[Dict[str, Any]] = []
    for deployment_version_id in deployment_version_ids:
        for model_version_id in model_version_ids:
            try:
                deployment_info = prodat_monitoring.get_deployment_info(deployment_version_id=deployment_version_id)
            except Exception:
                # if fetching fails for this deployment, skip it
                continue
            deployment_info = _process_deployment_info(deployment_info, model_version_id, deployment_version_id)
            deployments.append(deployment_info)

    return render_template("model_deployments.html", user=user, model=model, deployments=deployments)


@app.route("/<model_name>/deployments/<deployment_version_id>/<model_version_id>/custom/create")
def model_deployment_script_create(model_name: str, deployment_version_id: str, model_version_id: str):
    content = request.args.get("content", "")
    filepath = request.args.get("filepath")
    if not filepath:
        return "error", 400
    dirpath = os.path.dirname(filepath)
    os.makedirs(dirpath, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return "complete", 200


@app.route("/<model_name>/deployments/<deployment_version_id>/<model_version_id>/custom/run")
def model_deployment_script_run(model_name: str, deployment_version_id: str, model_version_id: str):
    filepath = request.args.get("filepath")
    if not filepath:
        return "error", 400
    if not os.path.isfile(filepath):
        return "error", 400
    # Run the file in a subprocess (safer than os.system)
    try:
        cmd = ["python", filepath]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return "error", 500
    return "complete", 200


@app.route("/hash/generate")
def generate_hash():
    string_to_hash = str(request.args.get("string_to_hash", ""))
    result_hash = str(uuid.uuid3(uuid.NAMESPACE_DNS, string_to_hash))
    return jsonify({"result": result_hash})


@app.route("/alias/create")
def create_alias():
    filepath = request.args.get("filepath")
    graph_id = request.args.get("graph_id")
    if not filepath or not graph_id:
        return jsonify({"error": "missing filepath or graph_id"}), 400

    available_filepath = Path(app.root_path) / "static" / "img" / f"{graph_id}.jpg"
    try:
        if available_filepath.exists():
            available_filepath.unlink()
        shutil.copy(src=filepath, dst=str(available_filepath))
    except Exception as e:
        return jsonify({"error": f"failed to copy file: {str(e)}"}), 500

    webpath = url_for("static", filename=f"img/{graph_id}.jpg")
    return jsonify({"webpath": webpath})


if __name__ == "__main__":
    app.run(debug=True)
