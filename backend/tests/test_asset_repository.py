from app.domain.assets import Asset, AssetStatus, AssetType
from app.infrastructure.asset_repository import SQLiteAssetRepository
from app.infrastructure.sqlite import SQLiteRepositories
from app.domain.projects import Project


def make_asset(asset_id="asset-1", project_id="project-1", sha256="a" * 64):
    return Asset(
        id=asset_id,
        project_id=project_id,
        type=AssetType.VIDEO,
        path=f"/storage/{sha256}",
        mime_type="video/mp4",
        size_bytes=123,
        sha256=sha256,
        status=AssetStatus.READY,
    )


def test_asset_create_is_idempotent_for_identical_commit(tmp_path):
    repositories = SQLiteRepositories(tmp_path / "assets.db")
    try:
        repositories.projects.create(Project(id="project-1", name="Test"))
        assets = SQLiteAssetRepository(repositories.store)
        first = assets.create(make_asset())
        second = assets.create(make_asset())

        assert first.id == second.id == "asset-1"
        assert assets.get("asset-1").sha256 == "a" * 64
        assert len(assets.list(project_id="project-1")) == 1
    finally:
        repositories.close()


def test_asset_create_rejects_id_reuse_with_different_content(tmp_path):
    repositories = SQLiteRepositories(tmp_path / "assets.db")
    try:
        repositories.projects.create(__import__("app.domain.projects", fromlist=["Project"]).Project(id="project-1", name="Test"))
        assets = SQLiteAssetRepository(repositories.store)
        assets.create(make_asset())

        import pytest
        with pytest.raises(ValueError, match="ASSET_ID_CONFLICT"):
            assets.create(make_asset(sha256="b" * 64))
    finally:
        repositories.close()
