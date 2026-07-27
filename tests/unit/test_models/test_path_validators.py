"""Unit tests for path-traversal validators in model classes (G3 security fix)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from controldesk_mcp.models.measurement import (
    MeasurementExportRecordingInput,
    MeasurementImportRecordingInput,
)
from controldesk_mcp.models.project import (
    ExperimentExportInput,
    ExperimentImportInput,
    ProjectBackupInput,
    ProjectOpenFromBackupInput,
)
from controldesk_mcp.models.recorder import RecorderMainExportInput, RecorderMainImportSignalsInput

# ── ProjectBackupInput ─────────────────────────────────────────────────────────


def test_project_backup_valid_absolute_path() -> None:
    obj = ProjectBackupInput(backup_path="C:\\Backups\\proj.zip")
    assert obj.backup_path == "C:\\Backups\\proj.zip"


def test_project_backup_rejects_relative_path() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        ProjectBackupInput(backup_path="Backups\\proj.zip")


def test_project_backup_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        ProjectBackupInput(backup_path="C:\\Backups\\..\\Windows\\proj.zip")


# ── ProjectOpenFromBackupInput ─────────────────────────────────────────────────


def test_project_open_from_backup_valid() -> None:
    obj = ProjectOpenFromBackupInput(backup_path="C:\\Backups\\proj.zip")
    assert obj.backup_path == "C:\\Backups\\proj.zip"


def test_project_open_from_backup_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        ProjectOpenFromBackupInput(backup_path="proj.zip")


def test_project_open_from_backup_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        ProjectOpenFromBackupInput(backup_path="C:\\..\\System32\\file.zip")


# ── ExperimentExportInput ──────────────────────────────────────────────────────


def test_experiment_export_valid() -> None:
    obj = ExperimentExportInput(export_path="C:\\Exports\\exp.dsa")
    assert obj.export_path == "C:\\Exports\\exp.dsa"


def test_experiment_export_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        ExperimentExportInput(export_path="exp.dsa")


def test_experiment_export_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        ExperimentExportInput(export_path="C:\\Exports\\..\\secret\\exp.dsa")


# ── ExperimentImportInput ──────────────────────────────────────────────────────


def test_experiment_import_valid() -> None:
    obj = ExperimentImportInput(import_path="C:\\Exports\\exp.dsa")
    assert obj.import_path == "C:\\Exports\\exp.dsa"


def test_experiment_import_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        ExperimentImportInput(import_path="exp.dsa")


def test_experiment_import_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        ExperimentImportInput(import_path="C:\\Exports\\..\\secret\\exp.dsa")


# ── MeasurementExportRecordingInput ───────────────────────────────────────────


def test_measurement_export_valid() -> None:
    obj = MeasurementExportRecordingInput(recording_index=0, export_path="C:\\exports\\rec.mf4")
    assert obj.export_path == "C:\\exports\\rec.mf4"


def test_measurement_export_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        MeasurementExportRecordingInput(recording_index=0, export_path="rec.mf4")


def test_measurement_export_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        MeasurementExportRecordingInput(
            recording_index=0, export_path="C:\\exports\\..\\Windows\\rec.mf4"
        )


# ── MeasurementImportRecordingInput ───────────────────────────────────────────


def test_measurement_import_valid() -> None:
    obj = MeasurementImportRecordingInput(import_path="C:\\archives\\rec.mf4")
    assert obj.import_path == "C:\\archives\\rec.mf4"


def test_measurement_import_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        MeasurementImportRecordingInput(import_path="rec.mf4")


def test_measurement_import_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        MeasurementImportRecordingInput(import_path="C:\\archives\\..\\Windows\\rec.mf4")


# ── RecorderMainExportInput ───────────────────────────────────────────────────


def test_recorder_export_valid() -> None:
    obj = RecorderMainExportInput(full_path="C:\\Recordings\\rec.mf4r")
    assert obj.full_path == "C:\\Recordings\\rec.mf4r"


def test_recorder_export_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        RecorderMainExportInput(full_path="rec.mf4r")


def test_recorder_export_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        RecorderMainExportInput(full_path="C:\\Recordings\\..\\Windows\\rec.mf4r")


# ── RecorderMainImportSignalsInput ────────────────────────────────────────────


def test_recorder_import_signals_valid() -> None:
    obj = RecorderMainImportSignalsInput(full_path="C:\\Recordings\\rec.mf4r")
    assert obj.full_path == "C:\\Recordings\\rec.mf4r"


def test_recorder_import_signals_rejects_relative() -> None:
    with pytest.raises(ValidationError, match="absolute"):
        RecorderMainImportSignalsInput(full_path="rec.mf4r")


def test_recorder_import_signals_rejects_traversal() -> None:
    with pytest.raises(ValidationError, match="\\.\\."):
        RecorderMainImportSignalsInput(full_path="C:\\Recordings\\..\\Windows\\rec.mf4r")
