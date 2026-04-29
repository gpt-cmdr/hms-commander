"""Tests for HmsExamples extraction helpers."""

import json
import zipfile
from pathlib import Path

import pandas as pd

from hms_commander.HmsExamples import HmsExamples


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
