"""Test download counting functionality."""
from aiogithubapi import GitHubReleaseAssetModel
from aiogithubapi.models.release import GitHubReleaseModel


def test_find_target_asset_with_configured_filename(repository):
    """Test finding asset when filename is configured."""
    repository.data.file_name = "specific-file.js"

    assets = [
        GitHubReleaseAssetModel(
            {"name": "wrong-file.js", "download_count": 50}),
        GitHubReleaseAssetModel(
            {"name": "specific-file.js", "download_count": 200}),
        GitHubReleaseAssetModel(
            {"name": "another-file.js", "download_count": 150}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "specific-file.js"
    assert result.download_count == 200


def test_find_target_asset_plugin_patterns(repository_plugin):
    """Test finding asset for plugins using naming patterns."""
    repository = repository_plugin
    repository.data.full_name = "user/test-card"
    repository.data.file_name = None

    assets = [
        GitHubReleaseAssetModel({"name": "README.md", "download_count": 10}),
        GitHubReleaseAssetModel(
            {"name": "test-card.js", "download_count": 500}),
        GitHubReleaseAssetModel(
            {"name": "other-file.js", "download_count": 50}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "test-card.js"
    assert result.download_count == 500


def test_find_target_asset_plugin_bundle_pattern(repository_plugin):
    """Test finding asset for plugins using bundle pattern."""
    repository = repository_plugin
    repository.data.full_name = "user/test-card"
    repository.data.file_name = None

    assets = [
        GitHubReleaseAssetModel({"name": "README.md", "download_count": 10}),
        GitHubReleaseAssetModel(
            {"name": "test-card-bundle.js", "download_count": 300}),
        GitHubReleaseAssetModel(
            {"name": "other-file.js", "download_count": 50}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "test-card-bundle.js"
    assert result.download_count == 300


def test_find_target_asset_plugin_umd_pattern(repository_plugin):
    """Test finding asset for plugins using UMD pattern."""
    repository = repository_plugin
    repository.data.full_name = "user/test-card"
    repository.data.file_name = None

    assets = [
        GitHubReleaseAssetModel({"name": "README.md", "download_count": 10}),
        GitHubReleaseAssetModel(
            {"name": "test-card.umd.js", "download_count": 400}),
        GitHubReleaseAssetModel(
            {"name": "other-file.js", "download_count": 50}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "test-card.umd.js"
    assert result.download_count == 400


def test_find_target_asset_with_manifest_filename(repository):
    """Test finding asset using manifest filename."""
    repository.data.file_name = None
    repository.repository_manifest.filename = "manifest-specified.js"

    assets = [
        GitHubReleaseAssetModel(
            {"name": "wrong-file.js", "download_count": 50}),
        GitHubReleaseAssetModel(
            {"name": "manifest-specified.js", "download_count": 250}),
        GitHubReleaseAssetModel(
            {"name": "another-file.js", "download_count": 150}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "manifest-specified.js"
    assert result.download_count == 250


def test_find_target_asset_fallback_to_first(repository):
    """Test fallback to first asset when no specific match."""
    repository.data.file_name = None

    assets = [
        GitHubReleaseAssetModel(
            {"name": "first-file.zip", "download_count": 100}),
        GitHubReleaseAssetModel(
            {"name": "second-file.zip", "download_count": 200}),
        GitHubReleaseAssetModel(
            {"name": "third-file.zip", "download_count": 300}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "first-file.zip"
    assert result.download_count == 100


def test_find_target_asset_empty_assets(repository):
    """Test handling empty asset list."""
    result = repository._find_target_asset([])
    assert result is None


def test_find_target_asset_none_assets(repository):
    """Test handling None asset list."""
    result = repository._find_target_asset(None)
    assert result is None


def test_find_target_asset_priority_order(repository_plugin):
    """Test that specific filename takes priority over plugin patterns."""
    repository = repository_plugin
    repository.data.full_name = "user/test-card"
    repository.data.file_name = "specific-file.js"

    assets = [
        GitHubReleaseAssetModel(
            {"name": "test-card.js", "download_count": 100}),
        GitHubReleaseAssetModel(
            {"name": "specific-file.js", "download_count": 200}),
        GitHubReleaseAssetModel(
            {"name": "test-card-bundle.js", "download_count": 300}),
    ]

    result = repository._find_target_asset(assets)
    assert result is not None
    assert result.name == "specific-file.js"
    assert result.download_count == 200


def test_download_counting_with_single_asset(repository):
    """Test download counting with single asset."""
    repository.data.releases = True
    repository.data.file_name = "test.zip"
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [{"name": "test.zip", "download_count": 1500}]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 1500


def test_download_counting_with_multiple_assets(repository):
    """Test download counting with multiple assets."""
    repository.data.releases = True
    repository.data.file_name = "main.zip"
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "source-code.zip", "download_count": 5000},
            {"name": "main.zip", "download_count": 2000},
            {"name": "docs.pdf", "download_count": 100},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 2000


def test_download_counting_plugin_with_multiple_assets(repository_plugin):
    """Test download counting for plugin with multiple assets."""
    repository = repository_plugin
    repository.data.releases = True
    repository.data.full_name = "user/my-card"
    repository.data.file_name = None
    repository.ref = "v2.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v2.0.0",
        "assets": [
            {"name": "source-code.zip", "download_count": 8000},
            {"name": "my-card.js", "download_count": 3000},
            {"name": "README.md", "download_count": 50},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 3000


def test_download_counting_fallback_to_first_asset(repository):
    """Test download counting falls back to first asset when no specific match."""
    repository.data.releases = True
    repository.data.file_name = None
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "random-file.zip", "download_count": 1000},
            {"name": "another-file.tar.gz", "download_count": 500},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 1000


def test_download_counting_no_matching_release(repository):
    """Test download counting when no release matches the ref."""
    repository.data.releases = True
    repository.ref = "v2.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [{"name": "test.zip", "download_count": 1000}]
    })
    repository.releases.objects = [release]

    repository.data.downloads = 0

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 0


def test_download_counting_release_with_no_assets(repository):
    """Test download counting when release has no assets."""
    repository.data.releases = True
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": []
    })
    repository.releases.objects = [release]

    repository.data.downloads = 0

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 0


def test_regression_multiple_assets_first_not_selected(repository):
    """Test that the first asset is not always selected (regression test)."""
    repository.data.releases = True
    repository.data.file_name = "target-file.zip"
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "wrong-file.zip", "download_count": 10000},
            {"name": "target-file.zip", "download_count": 5000},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 5000


def test_regression_plugin_pattern_matching(repository_plugin):
    """Test that plugin assets are selected by pattern, not position."""
    repository = repository_plugin
    repository.data.releases = True
    repository.data.full_name = "user/test-component"
    repository.data.file_name = None
    repository.ref = "v1.0.0"

    release = GitHubReleaseModel({
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "README.md", "download_count": 50},
            {"name": "test-component.js", "download_count": 3000},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 3000


def test_regression_github_issue_4438_scenario(repository):
    """Test the specific scenario from GitHub issue #4438."""
    repository.data.releases = True
    repository.data.file_name = "mbapi2020.zip"
    repository.ref = "v2.5.0"

    release = GitHubReleaseModel({
        "tag_name": "v2.5.0",
        "assets": [
            {"name": "Source code (zip)", "download_count": 4000},
            {"name": "mbapi2020.zip", "download_count": 190},
        ]
    })
    repository.releases.objects = [release]

    for release in repository.releases.objects:
        if release.tag_name == repository.ref:
            if assets := release.assets:
                target_asset = repository._find_target_asset(assets)
                if target_asset:
                    repository.data.downloads = target_asset.download_count

    assert repository.data.downloads == 190
