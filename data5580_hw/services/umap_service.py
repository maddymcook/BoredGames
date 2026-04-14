import hashlib
import json
import os
import pickle
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from umap import UMAP


class UMAPEmbeddingService:
    DEFAULT_PARAMS: Dict[str, Any] = {
        "n_neighbors": 15,
        "min_dist": 0.1,
        "n_components": 2,
        "metric": "euclidean",
        "random_state": 42,
        "n_jobs": -1,
    }

    _ALLOWED_UMAP_PARAMS = {
        "n_neighbors",
        "min_dist",
        "n_components",
        "metric",
        "random_state",
        "n_jobs",
    }

    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = Path(
            persist_dir or os.environ.get("UMAP_PERSIST_DIR", ".umap_cache")
        ).resolve()
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._model_cache: Dict[str, UMAP] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_lock(self, key: str) -> threading.Lock:
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def _canonical_key(self, params: Dict[str, Any], n_features: int) -> str:
        payload = {"params": params, "n_features": n_features}
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]

    def _paths(self, key: str) -> Tuple[Path, Path]:
        model_path = self._persist_dir / f"umap_model_{key}.pkl"
        training_path = self._persist_dir / f"umap_training_{key}.npy"
        return model_path, training_path

    def _min_samples_required(self, params: Dict[str, Any]) -> int:
        # Require a minimal warm-up corpus but avoid forcing default
        # n_neighbors=15 before first fit on small assignments/test sets.
        n_components = int(params.get("n_components", 2))
        return max(n_components + 1, 3)

    def _load_training_matrix(self, training_path: Path) -> Optional[np.ndarray]:
        if not training_path.exists():
            return None
        return np.load(training_path)

    def _save_training_matrix(self, training_path: Path, X: np.ndarray) -> None:
        np.save(training_path, X)

    def _load_model(self, model_path: Path) -> Optional[UMAP]:
        if not model_path.exists():
            return None
        with model_path.open("rb") as f:
            return pickle.load(f)

    def _save_model(self, model_path: Path, model: UMAP) -> None:
        with model_path.open("wb") as f:
            pickle.dump(model, f)

    def compute_embeddings(
        self,
        X: np.ndarray,
        umap_params: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]:
        if X is None:
            raise ValueError("UMAP embedding input X cannot be null.")

        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if X.ndim != 2:
            raise ValueError(f"UMAP embedding input must be 2D, got shape {X.shape}.")

        n_samples, n_features = X.shape
        if n_samples < 1:
            raise ValueError("UMAP embedding input must contain at least one sample.")

        params = dict(self.DEFAULT_PARAMS)
        if umap_params:
            params.update({k: v for k, v in umap_params.items() if v is not None})

        filtered_params = {
            k: v for k, v in params.items() if k in self._ALLOWED_UMAP_PARAMS
        }

        if n_features < 2:
            n_components = int(filtered_params.get("n_components", 2))
            return [[0.0] * n_components for _ in range(n_samples)]

        key = self._canonical_key(filtered_params, n_features=n_features)
        model_path, training_path = self._paths(key)
        lock = self._get_lock(key)

        with lock:
            model = self._model_cache.get(key)
            if model is None:
                model = self._load_model(model_path)
                if model is not None:
                    self._model_cache[key] = model

            historical = self._load_training_matrix(training_path)
            if historical is None:
                combined = X.copy()
            else:
                combined = np.vstack([historical, X])
            self._save_training_matrix(training_path, combined)

            if model is None:
                sample_count = combined.shape[0]
                min_required = self._min_samples_required(filtered_params)
                if sample_count < min_required:
                    raise ValueError(
                        "UMAP model is not fitted yet. "
                        f"Collected {sample_count} rows, need at least {min_required}. "
                        "Send more inferences or a batch to warm up the embedding model."
                    )

                effective_params = dict(filtered_params)
                effective_params["n_neighbors"] = min(
                    max(int(effective_params.get("n_neighbors", 15)), 2),
                    sample_count - 1,
                )

                model = UMAP(**effective_params)
                model.fit(combined)
                self._save_model(model_path, model)
                self._model_cache[key] = model

            embeddings = model.transform(X)
            return embeddings.astype(float).tolist()


umap_embedding_service = UMAPEmbeddingService()