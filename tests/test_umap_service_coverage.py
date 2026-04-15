import numpy as np
import pytest

from data5580_hw.services.umap_service import UMAPEmbeddingService


def test_compute_embeddings_raises_on_none(tmp_path):
    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    with pytest.raises(ValueError, match="cannot be null"):
        svc.compute_embeddings(None)


def test_compute_embeddings_raises_on_wrong_ndim(tmp_path):
    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.zeros((2, 2, 2), dtype=float)  # 3D array is invalid
    with pytest.raises(ValueError, match=r"must be 2D"):
        svc.compute_embeddings(X)


def test_compute_embeddings_raises_on_empty(tmp_path):
    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.empty((0, 3), dtype=float)
    with pytest.raises(ValueError, match="at least one sample"):
        svc.compute_embeddings(X)


def test_compute_embeddings_multi_sample_insufficient_samples_raises_warmup(tmp_path):
    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))

    # n_samples=2 is below default minimum required rows for first fit.
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=float)
    with pytest.raises(ValueError, match="not fitted yet"):
        svc.compute_embeddings(X, umap_params={"n_components": 2})


def test_compute_embeddings_ignores_unknown_umap_params(tmp_path):
    svc = UMAPEmbeddingService(persist_dir=str(tmp_path))
    X = np.random.RandomState(0).rand(8, 3)

    # Should not error: unknown params are filtered out.
    embeddings = svc.compute_embeddings(
        X, umap_params={"n_components": 2, "definitely_not_real": 123}
    )

    assert isinstance(embeddings, list)
    assert len(embeddings) == 8
    assert len(embeddings[0]) == 2

