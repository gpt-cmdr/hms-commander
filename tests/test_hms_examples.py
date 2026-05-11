"""Tests for HmsExamples extraction helpers."""

import hashlib
import io
import importlib
import json
import zipfile
from pathlib import Path

import pandas as pd

from hms_commander.HmsExamples import HmsExamples

HmsExamplesModule = importlib.import_module("hms_commander.HmsExamples")


class FakeScienceBaseResponse:
    """Minimal requests.Response test double for ScienceBase calls."""

    def __init__(self, content=b"", payload=None, headers=None):
        self.content = content
        self.payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

    def iter_content(self, chunk_size=8192):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]


def _sciencebase_zip_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("HEC_HMS_Validation/hahn_valid.hms", "Project: hahn_valid\n")
        zf.writestr(
            "HEC_HMS_Validation/hahn_valid_CN.basin",
            "Basin: hahn_valid_CN\n",
        )
    return buffer.getvalue()


def test_extract_project_supports_suffix(tmp_path, monkeypatch):
    install_path = tmp_path / "HEC-HMS" / "4.13"
    install_path.mkdir(parents=True)
    samples_zip = install_path / "samples.zip"

    with zipfile.ZipFile(samples_zip, "w") as zf:
        zf.writestr("samples/castro/castro.hms", "Project: castro\n")
        zf.writestr("samples/castro/castro.basin", "Basin: castro\n")

    monkeypatch.setattr(
        HmsExamples,
        "_installed_versions",
        {"4.13": install_path},
    )
    monkeypatch.setattr(
        HmsExamples,
        "_project_catalog",
        pd.DataFrame([
            {
                "version": "4.13",
                "project": "castro",
                "install_path": str(install_path),
                "samples_zip": str(samples_zip),
            }
        ]),
    )

    extracted = HmsExamples.extract_project(
        "castro",
        version="4.13",
        output_path=tmp_path / "example_projects",
        suffix="015 upstream",
    )

    assert extracted == tmp_path / "example_projects" / "castro_015_upstream"
    assert (extracted / "castro.hms").exists()
    assert HmsExamples.is_project_extracted(
        "castro",
        output_path=tmp_path / "example_projects",
        suffix="015 upstream",
    )


def test_list_sciencebase_projects_includes_hahn_arroyo():
    catalog = HmsExamples.list_sciencebase_projects()

    assert catalog.columns.tolist() == [
        "name",
        "sb_item_id",
        "description",
        "size_mb",
        "methods",
    ]
    row = catalog[catalog["name"] == "hahn_arroyo_validation"].iloc[0]
    assert row["sb_item_id"] == "5e6299ebe4b01d509257dcc3"
    assert row["size_mb"] == 5.18
    assert "SCS Curve Number" in row["methods"]


def test_extract_sciencebase_project_downloads_and_caches(
    tmp_path,
    monkeypatch,
):
    zip_bytes = _sciencebase_zip_bytes()
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("?format=json"):
            return FakeScienceBaseResponse(payload={
                "id": "5e6299ebe4b01d509257dcc3",
                "title": "HEC-HMS Validation Period Input and Output Data",
                "citation": "ScienceBase test citation.",
                "files": [
                    {
                        "name": "HEC_HMS_Validation.zip",
                        "size": len(zip_bytes),
                        "contentType": "application/zip",
                        "downloadUri": "https://example.test/HEC_HMS_Validation.zip",
                    },
                ],
            })
        return FakeScienceBaseResponse(
            content=zip_bytes,
            headers={"content-length": str(len(zip_bytes))},
        )

    monkeypatch.setattr(
        HmsExamples,
        "sciencebase_cache_dir",
        tmp_path / "sciencebase",
    )
    monkeypatch.setattr(HmsExamplesModule.requests, "get", fake_get)

    extracted = HmsExamples.extract_sciencebase_project("hahn_arroyo_validation")

    assert extracted == (
        tmp_path / "sciencebase" / "hahn_arroyo_validation" / "project"
    )
    assert (extracted / "hahn_valid.hms").exists()
    assert (extracted / "hahn_valid_CN.basin").exists()
    assert len(calls) == 2

    provenance = json.loads(
        (extracted / "SOURCE_SCIENCEBASE.json").read_text(encoding="utf-8")
    )
    assert provenance["source"] == "ScienceBase"
    assert provenance["project_name"] == "hahn_arroyo_validation"
    assert provenance["sb_item_id"] == "5e6299ebe4b01d509257dcc3"
    assert provenance["citation"] == "ScienceBase test citation."
    assert provenance["source_file_name"] == "HEC_HMS_Validation.zip"
    assert provenance["source_file_size"] == len(zip_bytes)
    assert (
        provenance["source_file_sha256"]
        == hashlib.sha256(zip_bytes).hexdigest()
    )


def test_extract_sciencebase_project_uses_valid_cache_without_network(
    tmp_path,
    monkeypatch,
):
    cache_project = (
        tmp_path / "sciencebase" / "hahn_arroyo_validation" / "project"
    )
    cache_project.mkdir(parents=True)
    (cache_project / "hahn_valid.hms").write_text(
        "Project: hahn_valid\n",
        encoding="utf-8",
    )
    (cache_project / "SOURCE_SCIENCEBASE.json").write_text(
        json.dumps({
            "source": "ScienceBase",
            "project_name": "hahn_arroyo_validation",
            "sb_item_id": "5e6299ebe4b01d509257dcc3",
            "source_file_name": "HEC_HMS_Validation.zip",
            "source_file_sha256": "known-good-hash",
        }),
        encoding="utf-8",
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("valid ScienceBase cache should not use network")

    monkeypatch.setattr(
        HmsExamples,
        "sciencebase_cache_dir",
        tmp_path / "sciencebase",
    )
    monkeypatch.setattr(HmsExamplesModule.requests, "get", fail_get)

    extracted = HmsExamples.extract_sciencebase_project("hahn-arroyo-validation")

    assert extracted == cache_project


def test_extract_sciencebase_project_copies_cached_project_to_output(
    tmp_path,
    monkeypatch,
):
    cache_project = (
        tmp_path / "sciencebase" / "hahn_arroyo_validation" / "project"
    )
    cache_project.mkdir(parents=True)
    (cache_project / "hahn_valid.hms").write_text(
        "Project: hahn_valid\n",
        encoding="utf-8",
    )
    (cache_project / "SOURCE_SCIENCEBASE.json").write_text(
        json.dumps({
            "source": "ScienceBase",
            "project_name": "hahn_arroyo_validation",
            "sb_item_id": "5e6299ebe4b01d509257dcc3",
            "source_file_name": "HEC_HMS_Validation.zip",
            "source_file_sha256": "known-good-hash",
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        HmsExamples,
        "sciencebase_cache_dir",
        tmp_path / "sciencebase",
    )

    extracted = HmsExamples.extract_sciencebase_project(
        "hahn_arroyo_validation",
        output_path=tmp_path / "example_projects",
    )

    assert extracted == tmp_path / "example_projects" / "hahn_arroyo_validation"
    assert (extracted / "hahn_valid.hms").exists()
    assert (extracted / "SOURCE_SCIENCEBASE.json").exists()


def test_extract_ebfe_project_copies_only_hms_project(tmp_path, monkeypatch):
    class FakeRasEbfeModels:
        @staticmethod
        def normalize_model_key(model_key):
            assert model_key == "maurepas"
            return "lake-maurepas"

        @staticmethod
        def available_models():
            return {
                "lake-maurepas": {
                    "study_area": "LakeMaurepas_08070204",
                    "huc8": "08070204",
                    "ras_version": "5.0.7",
                    "notes": "Test eBFE delivery.",
                }
            }

        @staticmethod
        def organize_model(model_key, download_root=None, output_root=None, **kwargs):
            assert model_key == "lake-maurepas"
            assert Path(download_root).name == "downloads"
            organized = Path(output_root) / "LakeMaurepas_08070204"
            hms_project = organized / "HMS Model" / "Lake_Maurepas"
            ras_project = organized / "RAS Model"
            hms_project.mkdir(parents=True)
            ras_project.mkdir(parents=True)
            (hms_project / "Lake_Maurepas.hms").write_text(
                "Project: Lake_Maurepas\n",
                encoding="utf-8",
            )
            (hms_project / "Lake_Maurepas.basin").write_text(
                "Basin: Lake_Maurepas\n",
                encoding="utf-8",
            )
            (ras_project / "do_not_copy.prj").write_text(
                "RAS project\n",
                encoding="utf-8",
            )
            return organized

    monkeypatch.setattr(
        HmsExamples,
        "_import_ras_ebfe_models",
        classmethod(lambda cls: FakeRasEbfeModels),
    )
    monkeypatch.setattr(
        HmsExamples,
        "_get_package_version",
        classmethod(lambda cls, package_name: "test-version"),
    )

    extracted = HmsExamples.extract_ebfe_project(
        "maurepas",
        output_path=tmp_path / "example_projects",
        suffix="015",
    )

    workspace = tmp_path / "example_projects" / "lake-maurepas_015"
    assert extracted == workspace / "hms" / "Lake_Maurepas"
    assert (extracted / "Lake_Maurepas.hms").exists()
    assert (extracted / "Lake_Maurepas.basin").exists()
    assert not (workspace / "hms" / "do_not_copy.prj").exists()

    provenance = json.loads((extracted / "SOURCE_EBFE.json").read_text())
    assert provenance["model_key"] == "lake-maurepas"
    assert provenance["huc8"] == "08070204"
    assert provenance["ras_commander_version"] == "test-version"


def test_list_ebfe_projects_uses_hms_validated_filter(monkeypatch):
    class FakeRasEbfeModels:
        @staticmethod
        def available_models():
            return {
                "lake-maurepas": {
                    "study_area": "LakeMaurepas_08070204",
                    "huc8": "08070204",
                    "ras_version": "5.0.7",
                    "notes": "Has HMS content.",
                },
                "spring-creek": {
                    "study_area": "SpringCreek_12040102",
                    "huc8": "12040102",
                    "ras_version": "5.0.7",
                    "notes": "RAS-only delivery.",
                },
            }

    monkeypatch.setattr(
        HmsExamples,
        "_import_ras_ebfe_models",
        classmethod(lambda cls: FakeRasEbfeModels),
    )

    hms_sources = HmsExamples.list_ebfe_projects()
    all_sources = HmsExamples.list_ebfe_projects(hms_only=False)

    assert hms_sources["key"].tolist() == ["lake-maurepas"]
    assert set(all_sources["key"]) == {"lake-maurepas", "spring-creek"}


def test_list_ebfe_projects_supports_legacy_ras_organizers(monkeypatch):
    class FakeLegacyRasEbfeModels:
        @staticmethod
        def organize_north_galveston_bay(*args, **kwargs):
            raise AssertionError("listing must not organize or download")

        @staticmethod
        def organize_spring_creek(*args, **kwargs):
            raise AssertionError("listing must not organize or download")

    monkeypatch.setattr(
        HmsExamples,
        "_import_ras_ebfe_models",
        classmethod(lambda cls: FakeLegacyRasEbfeModels),
    )

    hms_sources = HmsExamples.list_ebfe_projects()
    all_sources = HmsExamples.list_ebfe_projects(hms_only=False)

    assert hms_sources["key"].tolist() == ["north-galveston-bay"]
    assert set(all_sources["key"]) == {"north-galveston-bay", "spring-creek"}


def test_extract_ebfe_project_supports_legacy_ras_organizer(tmp_path, monkeypatch):
    class FakeLegacyRasEbfeModels:
        @staticmethod
        def organize_north_galveston_bay(
            downloaded_folder,
            output_folder=None,
            extract_ras_nested=False,
            validate_dss=True,
        ):
            assert Path(downloaded_folder).name == "downloads"
            assert Path(output_folder).name == "NorthGalvestonBay_12040203"
            assert extract_ras_nested is False
            assert validate_dss is False

            organized = Path(output_folder)
            hms_project = organized / "HMS Model" / "NorthGalvestonBay"
            hms_project.mkdir(parents=True)
            (hms_project / "NorthGalvestonBay.hms").write_text(
                "Project: NorthGalvestonBay\n",
                encoding="utf-8",
            )
            (hms_project / "NorthGalvestonBay.basin").write_text(
                "Basin: NorthGalvestonBay\n",
                encoding="utf-8",
            )
            return organized

    monkeypatch.setattr(
        HmsExamples,
        "_import_ras_ebfe_models",
        classmethod(lambda cls: FakeLegacyRasEbfeModels),
    )
    monkeypatch.setattr(
        HmsExamples,
        "_get_package_version",
        classmethod(lambda cls, package_name: "legacy-version"),
    )

    extracted = HmsExamples.extract_ebfe_project(
        "12040203",
        output_path=tmp_path / "example_projects",
        suffix="015",
        extract_ras_nested=False,
        validate_dss=False,
    )

    workspace = tmp_path / "example_projects" / "north-galveston-bay_015"
    assert extracted == workspace / "hms" / "NorthGalvestonBay"
    assert (extracted / "NorthGalvestonBay.hms").exists()

    provenance = json.loads((extracted / "SOURCE_EBFE.json").read_text())
    assert provenance["model_key"] == "north-galveston-bay"
    assert provenance["huc8"] == "12040203"
    assert provenance["ras_commander_version"] == "legacy-version"
