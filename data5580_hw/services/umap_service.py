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
    """
    Computes UMAP embeddings and persists the fitted model across calls.

    Note: UMAP requires enough samples to fit. If a model is not yet fitted
    and there are insufficient samples, this service raises a ValueError
    with a descriptive message.
    """

    DEFAULT_PARAMS: Dict[str, Any] = {
        # Keep defaults intentionally small so the service can fit quickly
        # when the API is called with a small number of samples.
        "n_neighbors": 1,
        "min_dist": 0.1,
        "n_components": 2,
        "metric": "euclidean",
        "random_state": 42,
        "n_jobs": -1,
    }

    _ALLOWED_UMAP_PARAMS = {"n_neighbors", "min_dist", "n_components", "metric", "random_state", "n_jobs"}

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
        # UMAP needs enough samples to build a neighbor graph.
        n_neighbors = int(params.get("n_neighbors", 15))
        n_components = int(params.get("n_components", 2))
        # `n_neighbors + 1` ensures n_neighbors < n_samples.
        # `n_components` ensures the embedding dimensionality is feasible.
        return max(n_neighbors + 1, n_components)

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
        """
        Args:
            X: numpy array of shape (n_samples, n_features)
            umap_params: UMAP hyperparameters overriding defaults

        Returns:
            embeddings: list of shape (n_samples, n_components)
        """
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

        # Filter to the parameters that UMAP understands.
        filtered_params = {
            k: v for k, v in params.items() if k in self._ALLOWED_UMAP_PARAMS
        }

        # UMAP can't be fit on a single sample.
        # Since this API commonly receives `features` as a single row (`n_samples == 1`),
        # we fall back to treating each feature dimension as a "sample" and then
        # aggregate the resulting embeddings into a single vector for the input row.
        if n_samples == 1:
            if n_features < 2:
                # Degenerate case: no meaningful manifold can be learned.
                n_components = int(filtered_params.get("n_components", 2))
                return [[0.0] * n_components]

            X_alt = X.T  # (n_features, 1)
            n_alt_samples = X_alt.shape[0]

            n_neighbors = int(filtered_params.get("n_neighbors", 15))
            filtered_params["n_neighbors"] = min(n_neighbors, n_alt_samples - 1)
            if filtered_params["n_neighbors"] < 1:
                filtered_params["n_neighbors"] = 1

            model = UMAP(**filtered_params)
            embeddings_alt = model.fit_transform(X_alt)
            embedding = embeddings_alt.mean(axis=0)  # (n_components,)
            return [embedding.astype(float).tolist()]

        # Multi-sample case: fit once (first time for a given param+feature shape),
        # persist, and reuse on subsequent calls for consistent embeddings.
        n_neighbors = int(filtered_params.get("n_neighbors", 15))
        filtered_params["n_neighbors"] = min(n_neighbors, n_samples - 1)
        if filtered_params["n_neighbors"] < 1:
            filtered_params["n_neighbors"] = 1

        key = self._canonical_key(filtered_params, n_features=n_features)
        model_path, _training_path = self._paths(key)
        lock = self._get_lock(key)

        with lock:
            model = self._model_cache.get(key)
            if model is None:
                model = self._load_model(model_path)
                if model is not None:
                    self._model_cache[key] = model

            if model is None:
                model = UMAP(**filtered_params)
                model.fit(X)
                self._save_model(model_path, model)
                self._model_cache[key] = model

            embeddings = model.transform(X)
            return embeddings.astype(float).tolist()


umap_embedding_service = UMAPEmbeddingService()

