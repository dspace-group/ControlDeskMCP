"""Unit tests for measurement MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.measurement import (
    DataLoggerConfigureResult,
    DataLoggerCreateResult,
    DataLoggerListResult,
    DataLoggerManageAction,
    DataLoggerManageInput,
    DataLoggerRemoveResult,
    DataLoggerStartResult,
    DataLoggerStopResult,
    MeasurementBookmarkAddResult,
    MeasurementBookmarkListResult,
    MeasurementBookmarkRemoveResult,
    MeasurementConfigureBufferResult,
    MeasurementConfigureSettingsResult,
    MeasurementDiscoverResult,
    MeasurementExportRecordingResult,
    MeasurementGetConfigurationResult,
    MeasurementGetStateResult,
    MeasurementImportRecordingResult,
    MeasurementListRecordingsResult,
    MeasurementListSignalsResult,
    MeasurementManageAction,
    MeasurementManageInput,
    MeasurementQueryAction,
    MeasurementQueryInput,
    MeasurementRasterAddResult,
    MeasurementRasterListResult,
    MeasurementRasterManageAction,
    MeasurementRasterManageInput,
    MeasurementRasterRemoveResult,
    MeasurementSignalAddResult,
    MeasurementSignalRemoveResult,
    MeasurementStartInput,
    MeasurementStartResult,
    MeasurementStopInput,
    MeasurementStopResult,
    RecordingManageAction,
    RecordingManageInput,
    TriggerConditionTimeLimitResult,
    TriggerConditionTriggerBasedResult,
    TriggerManageAction,
    TriggerManageInput,
    TriggerRuleCreateResult,
    TriggerRuleRemoveResult,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.measurement_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── Tool 1: measurement_start ─────────────────────────────────────────────────


class TestMeasurementStart:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = MeasurementStartResult(
            started=True, platforms_measuring=["XCP"], timestamp_utc=_TS
        )
        with _patch_svc("start_measurement", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_start

            result = await measurement_start(MeasurementStartInput())

        assert isinstance(result, MeasurementStartResult)
        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("start_measurement", return_value=_ERROR):
            from controldesk_mcp.tools.measurement.management import measurement_start

            result = await measurement_start(MeasurementStartInput())

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── Tool 2: measurement_stop ──────────────────────────────────────────────────


class TestMeasurementStop:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = MeasurementStopResult(stopped=True, timestamp_utc=_TS)
        with _patch_svc("stop_measurement", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_stop

            result = await measurement_stop(MeasurementStopInput())

        assert isinstance(result, MeasurementStopResult)
        assert result["stopped"] is True


# ── Tool 3: measurement_manage ────────────────────────────────────────────────


class TestMeasurementQuery:
    @pytest.mark.asyncio
    async def test_get_state(self) -> None:
        expected = MeasurementGetStateResult(
            state="Measuring", is_measuring=True, timestamp_utc=_TS
        )
        with _patch_svc("get_measurement_state", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_query

            result = await measurement_query(
                MeasurementQueryInput(action=MeasurementQueryAction.get_state)
            )

        assert isinstance(result, MeasurementGetStateResult)
        assert result["is_measuring"] is True

    @pytest.mark.asyncio
    async def test_get_configuration(self) -> None:
        expected = MeasurementGetConfigurationResult(buffer={}, signal_count=2, timestamp_utc=_TS)
        with _patch_svc("get_configuration", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_query

            result = await measurement_query(
                MeasurementQueryInput(action=MeasurementQueryAction.get_configuration)
            )

        assert isinstance(result, MeasurementGetConfigurationResult)
        assert result["signal_count"] == 2

    @pytest.mark.asyncio
    async def test_list_signals(self) -> None:
        expected = MeasurementListSignalsResult(total_count=2, signals=[], has_more=False)
        with _patch_svc("list_signals", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_query

            result = await measurement_query(
                MeasurementQueryInput(action=MeasurementQueryAction.list_signals)
            )

        assert isinstance(result, MeasurementListSignalsResult)


class TestMeasurementManage:
    @pytest.mark.asyncio
    async def test_configure_buffer(self) -> None:
        expected = MeasurementConfigureBufferResult(
            configured=True,
            buffer_size_seconds=10.0,
            warning_enabled=False,
            warning_time_seconds=3.0,
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_buffer", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_manage

            result = await measurement_manage(
                MeasurementManageInput(
                    action=MeasurementManageAction.configure_buffer,
                    buffer_size_seconds=10.0,
                )
            )

        assert isinstance(result, MeasurementConfigureBufferResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_configure_buffer_missing_param(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_manage

        result = await measurement_manage(
            MeasurementManageInput(
                action=MeasurementManageAction.configure_buffer,
                buffer_size_seconds=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure_settings(self) -> None:
        expected = MeasurementConfigureSettingsResult(
            configured=True,
            data_pool_path="C:\\Data",
            auto_save_enabled=True,
            auto_save_format="MF4",
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_settings", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_manage

            result = await measurement_manage(
                MeasurementManageInput(
                    action=MeasurementManageAction.configure_settings,
                    data_pool_path="C:\\Data",
                )
            )

        assert isinstance(result, MeasurementConfigureSettingsResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_signal_add(self) -> None:
        expected = MeasurementSignalAddResult(
            added=True,
            connection_path="XCP(5ms)://ctrl",
            variable_name="ctrl",
            platform_name="XCP",
            raster_name="5ms",
            is_connected=True,
            active=True,
            recording_enabled=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("signal_add", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_manage

            result = await measurement_manage(
                MeasurementManageInput(
                    action=MeasurementManageAction.signal_add,
                    connection_path="XCP(5ms)://ctrl",
                )
            )

        assert isinstance(result, MeasurementSignalAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_signal_add_missing_param(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_manage

        result = await measurement_manage(
            MeasurementManageInput(action=MeasurementManageAction.signal_add)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_signal_remove(self) -> None:
        expected = MeasurementSignalRemoveResult(
            removed=True, connection_path="XCP(5ms)://ctrl", timestamp_utc=_TS
        )
        with _patch_svc("signal_remove", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_manage

            result = await measurement_manage(
                MeasurementManageInput(
                    action=MeasurementManageAction.signal_remove,
                    connection_path="XCP(5ms)://ctrl",
                )
            )

        assert isinstance(result, MeasurementSignalRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_signal_remove_missing_param(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_manage

        result = await measurement_manage(
            MeasurementManageInput(action=MeasurementManageAction.signal_remove)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── Tool 4: measurement_raster_manage ────────────────────────────────────────


class TestMeasurementRasterManage:
    @pytest.mark.asyncio
    async def test_raster_add(self) -> None:
        expected = MeasurementRasterAddResult(
            added=True,
            platform_name="XCP",
            raster_name="XCP_5ms",
            raster_interval_ms=5.0,
            timestamp_utc=_TS,
        )
        with _patch_svc("add_raster", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_raster_manage

            result = await measurement_raster_manage(
                MeasurementRasterManageInput(
                    action=MeasurementRasterManageAction.raster_add,
                    platform_name="XCP",
                    raster_interval_ms=5.0,
                )
            )

        assert isinstance(result, MeasurementRasterAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_raster_add_missing_platform(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_raster_manage

        result = await measurement_raster_manage(
            MeasurementRasterManageInput(
                action=MeasurementRasterManageAction.raster_add,
                raster_interval_ms=5.0,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_raster_add_missing_interval(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_raster_manage

        result = await measurement_raster_manage(
            MeasurementRasterManageInput(
                action=MeasurementRasterManageAction.raster_add,
                platform_name="XCP",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_raster_list(self) -> None:
        expected = MeasurementRasterListResult(total_rasters=1, rasters=[], has_more=False)
        with _patch_svc("list_rasters", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_raster_manage

            result = await measurement_raster_manage(
                MeasurementRasterManageInput(action=MeasurementRasterManageAction.raster_list)
            )

        assert isinstance(result, MeasurementRasterListResult)

    @pytest.mark.asyncio
    async def test_raster_list_returns_error(self) -> None:
        with _patch_svc("list_rasters", return_value=_ERROR):
            from controldesk_mcp.tools.measurement.management import measurement_raster_manage

            result = await measurement_raster_manage(
                MeasurementRasterManageInput(action=MeasurementRasterManageAction.raster_list)
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_raster_remove(self) -> None:
        expected = MeasurementRasterRemoveResult(
            removed=True, platform_name="XCP", raster_name="XCP_5ms", timestamp_utc=_TS
        )
        with _patch_svc("remove_raster", return_value=expected):
            from controldesk_mcp.tools.measurement.management import measurement_raster_manage

            result = await measurement_raster_manage(
                MeasurementRasterManageInput(
                    action=MeasurementRasterManageAction.raster_remove,
                    platform_name="XCP",
                    raster_name="XCP_5ms",
                )
            )

        assert isinstance(result, MeasurementRasterRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_raster_remove_missing_platform(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_raster_manage

        result = await measurement_raster_manage(
            MeasurementRasterManageInput(
                action=MeasurementRasterManageAction.raster_remove,
                raster_name="XCP_5ms",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_raster_remove_missing_raster_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_raster_manage

        result = await measurement_raster_manage(
            MeasurementRasterManageInput(
                action=MeasurementRasterManageAction.raster_remove,
                platform_name="XCP",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── Tool 5: trigger_manage ────────────────────────────────────────────────────


class TestTriggerManage:
    @pytest.mark.asyncio
    async def test_rule_create(self) -> None:
        expected = TriggerRuleCreateResult(
            created=True,
            rule_name="StartCond",
            expression="ctrl < -0.1",
            mappings={"ctrl": "XCP(5ms)://ctrl"},
            enabled=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("create_trigger_rule", return_value=expected):
            from controldesk_mcp.tools.measurement.management import trigger_manage

            result = await trigger_manage(
                TriggerManageInput(
                    action=TriggerManageAction.rule_create,
                    rule_name="StartCond",
                    expression="ctrl < -0.1",
                    signal_mappings={"ctrl": "XCP(5ms)://ctrl"},
                )
            )

        assert isinstance(result, TriggerRuleCreateResult)
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_rule_create_missing_rule_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(
                action=TriggerManageAction.rule_create,
                expression="ctrl < 0",
                signal_mappings={"ctrl": "XCP(5ms)://ctrl"},
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rule_create_missing_expression(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(
                action=TriggerManageAction.rule_create,
                rule_name="Rule1",
                signal_mappings={"ctrl": "XCP(5ms)://ctrl"},
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rule_create_missing_signal_mappings(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(
                action=TriggerManageAction.rule_create,
                rule_name="Rule1",
                expression="ctrl < 0",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rule_remove(self) -> None:
        expected = TriggerRuleRemoveResult(removed=True, rule_name="StartCond", timestamp_utc=_TS)
        with _patch_svc("remove_trigger_rule", return_value=expected):
            from controldesk_mcp.tools.measurement.management import trigger_manage

            result = await trigger_manage(
                TriggerManageInput(
                    action=TriggerManageAction.rule_remove,
                    rule_name="StartCond",
                )
            )

        assert isinstance(result, TriggerRuleRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_rule_remove_missing_rule_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(TriggerManageInput(action=TriggerManageAction.rule_remove))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_condition_time_limit(self) -> None:
        expected = TriggerConditionTimeLimitResult(
            configured=True,
            condition_type="TimeLimit",
            enabled=True,
            time_limit_seconds=30.0,
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_time_limit_condition", return_value=expected):
            from controldesk_mcp.tools.measurement.management import trigger_manage

            result = await trigger_manage(
                TriggerManageInput(
                    action=TriggerManageAction.condition_time_limit,
                    enabled=True,
                    time_limit_seconds=30.0,
                )
            )

        assert isinstance(result, TriggerConditionTimeLimitResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_condition_time_limit_missing_enabled(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(
                action=TriggerManageAction.condition_time_limit,
                time_limit_seconds=30.0,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_condition_time_limit_missing_time_limit(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(
                action=TriggerManageAction.condition_time_limit,
                enabled=True,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_condition_trigger_based(self) -> None:
        expected = TriggerConditionTriggerBasedResult(
            configured=True,
            condition_type="start",
            rule_name="StartCond",
            enabled=True,
            trigger_delay_seconds=0.0,
            recording_cycles=1,
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_trigger_based_condition", return_value=expected):
            from controldesk_mcp.tools.measurement.management import trigger_manage

            result = await trigger_manage(
                TriggerManageInput(
                    action=TriggerManageAction.condition_trigger_based,
                    enabled=True,
                    condition_type="start",
                    rule_name="StartCond",
                )
            )

        assert isinstance(result, TriggerConditionTriggerBasedResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_condition_trigger_based_missing_params(self) -> None:
        from controldesk_mcp.tools.measurement.management import trigger_manage

        result = await trigger_manage(
            TriggerManageInput(action=TriggerManageAction.condition_trigger_based)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── Tool 6: recording_manage ──────────────────────────────────────────────────


class TestRecordingManage:
    @pytest.mark.asyncio
    async def test_list_recordings(self) -> None:
        expected = MeasurementListRecordingsResult(total_count=1, recordings=[], has_more=False)
        with _patch_svc("list_recordings", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(action=RecordingManageAction.list_recordings)
            )

        assert isinstance(result, MeasurementListRecordingsResult)

    @pytest.mark.asyncio
    async def test_export_recording(self) -> None:
        expected = MeasurementExportRecordingResult(
            exported=True,
            export_path="C:\\Exports\\rec.mf4",
            file_size_bytes=1024,
            timestamp_utc=_TS,
        )
        with _patch_svc("export_recording", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(
                    action=RecordingManageAction.export_recording,
                    recording_index=0,
                    export_path="C:\\Exports\\rec.mf4",
                )
            )

        assert isinstance(result, MeasurementExportRecordingResult)
        assert result["exported"] is True

    @pytest.mark.asyncio
    async def test_export_recording_missing_index(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(
                action=RecordingManageAction.export_recording,
                export_path="C:\\Exports\\rec.mf4",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_export_recording_missing_path(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(
                action=RecordingManageAction.export_recording,
                recording_index=0,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_export_recording_relative_path(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(
                action=RecordingManageAction.export_recording,
                recording_index=0,
                export_path="relative/path/rec.mf4",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "INVALID_PARAM"

    @pytest.mark.asyncio
    async def test_import_recording(self) -> None:
        expected = MeasurementImportRecordingResult(
            imported=True,
            import_path="C:\\Archives\\rec.mf4",
            new_recording_index=2,
            filename="rec.mf4",
            timestamp_utc=_TS,
        )
        with _patch_svc("import_recording", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(
                    action=RecordingManageAction.import_recording,
                    import_path="C:\\Archives\\rec.mf4",
                )
            )

        assert isinstance(result, MeasurementImportRecordingResult)
        assert result["imported"] is True

    @pytest.mark.asyncio
    async def test_import_recording_missing_path(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(action=RecordingManageAction.import_recording)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_import_recording_relative_path(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(
                action=RecordingManageAction.import_recording,
                import_path="relative/path.mf4",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "INVALID_PARAM"

    @pytest.mark.asyncio
    async def test_bookmark_add(self) -> None:
        expected = MeasurementBookmarkAddResult(
            added=True,
            title="Throttle spike",
            description="",
            timestamp_utc=_TS,
            bookmark_timestamp=_TS,
        )
        with _patch_svc("add_bookmark", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(
                    action=RecordingManageAction.bookmark_add,
                    title="Throttle spike",
                )
            )

        assert isinstance(result, MeasurementBookmarkAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_bookmark_add_missing_title(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(action=RecordingManageAction.bookmark_add)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_bookmark_list(self) -> None:
        expected = MeasurementBookmarkListResult(
            recording_index=0, total_bookmarks=2, bookmarks=[], has_more=False
        )
        with _patch_svc("list_bookmarks", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(
                    action=RecordingManageAction.bookmark_list,
                    recording_index=0,
                )
            )

        assert isinstance(result, MeasurementBookmarkListResult)

    @pytest.mark.asyncio
    async def test_bookmark_list_missing_index(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(action=RecordingManageAction.bookmark_list)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_bookmark_remove(self) -> None:
        expected = MeasurementBookmarkRemoveResult(
            removed=True, recording_index=0, bookmark_index=1, timestamp_utc=_TS
        )
        with _patch_svc("remove_bookmark", return_value=expected):
            from controldesk_mcp.tools.measurement.management import recording_manage

            result = await recording_manage(
                RecordingManageInput(
                    action=RecordingManageAction.bookmark_remove,
                    recording_index=0,
                    bookmark_index=1,
                )
            )

        assert isinstance(result, MeasurementBookmarkRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_bookmark_remove_missing_index(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(action=RecordingManageAction.bookmark_remove)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_bookmark_remove_missing_bookmark_index(self) -> None:
        from controldesk_mcp.tools.measurement.management import recording_manage

        result = await recording_manage(
            RecordingManageInput(
                action=RecordingManageAction.bookmark_remove,
                recording_index=0,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── Tool 7: data_logger_manage ────────────────────────────────────────────────


class TestDataLoggerManage:
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        expected = DataLoggerCreateResult(created=True, logger_name="CAN_Logger", timestamp_utc=_TS)
        with _patch_svc("create_data_logger", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(
                    action=DataLoggerManageAction.create,
                    logger_name="CAN_Logger",
                )
            )

        assert isinstance(result, DataLoggerCreateResult)
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_create_missing_logger_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(
            DataLoggerManageInput(action=DataLoggerManageAction.create)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure(self) -> None:
        expected = DataLoggerConfigureResult(
            configured=True,
            logger_name="CAN_Logger",
            output_file_path="C:\\Logs\\can.mf4",
            file_format="MF4",
            overwrite_existing=True,
        )
        with _patch_svc("configure_data_logger", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(
                    action=DataLoggerManageAction.configure,
                    logger_name="CAN_Logger",
                    output_file_path="C:\\Logs\\can.mf4",
                )
            )

        assert isinstance(result, DataLoggerConfigureResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_configure_missing_logger_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(
            DataLoggerManageInput(
                action=DataLoggerManageAction.configure,
                output_file_path="C:\\Logs\\can.mf4",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure_missing_output_path(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(
            DataLoggerManageInput(
                action=DataLoggerManageAction.configure,
                logger_name="CAN_Logger",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_start(self) -> None:
        expected = DataLoggerStartResult(started=True, logger_name="CAN_Logger", timestamp_utc=_TS)
        with _patch_svc("start_data_logger", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(
                    action=DataLoggerManageAction.start,
                    logger_name="CAN_Logger",
                )
            )

        assert isinstance(result, DataLoggerStartResult)
        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_start_missing_logger_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(
            DataLoggerManageInput(action=DataLoggerManageAction.start)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        expected = DataLoggerStopResult(stopped=True, logger_name="CAN_Logger", timestamp_utc=_TS)
        with _patch_svc("stop_data_logger", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(
                    action=DataLoggerManageAction.stop,
                    logger_name="CAN_Logger",
                )
            )

        assert isinstance(result, DataLoggerStopResult)
        assert result["stopped"] is True

    @pytest.mark.asyncio
    async def test_stop_missing_logger_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(DataLoggerManageInput(action=DataLoggerManageAction.stop))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        expected = DataLoggerListResult(total_loggers=1, loggers=[], has_more=False)
        with _patch_svc("list_data_loggers", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(action=DataLoggerManageAction.list)
            )

        assert isinstance(result, DataLoggerListResult)

    @pytest.mark.asyncio
    async def test_remove(self) -> None:
        expected = DataLoggerRemoveResult(removed=True, logger_name="CAN_Logger", timestamp_utc=_TS)
        with _patch_svc("remove_data_logger", return_value=expected):
            from controldesk_mcp.tools.measurement.management import data_logger_manage

            result = await data_logger_manage(
                DataLoggerManageInput(
                    action=DataLoggerManageAction.remove,
                    logger_name="CAN_Logger",
                )
            )

        assert isinstance(result, DataLoggerRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_logger_name(self) -> None:
        from controldesk_mcp.tools.measurement.management import data_logger_manage

        result = await data_logger_manage(
            DataLoggerManageInput(action=DataLoggerManageAction.remove)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── Tool 8: measurement_discover ──────────────────────────────────────────────


class TestMeasurementDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.measurement.management import measurement_discover

        result = await measurement_discover(AsyncMock())

        assert isinstance(result, MeasurementDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 5
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "measurement_query" in tool_names
        assert "measurement_raster_manage" in tool_names
        assert "trigger_manage" in tool_names
        assert "recording_manage" in tool_names
        assert "data_logger_manage" in tool_names


# ── Input model instantiation ─────────────────────────────────────────────────


class TestMeasurementInputModels:
    def test_no_arg_input_models_instantiate(self) -> None:
        assert MeasurementStartInput() is not None
        assert MeasurementStopInput() is not None

    def test_manage_input_instantiates(self) -> None:
        assert MeasurementManageInput(action=MeasurementManageAction.configure_buffer) is not None
        assert MeasurementQueryInput(action=MeasurementQueryAction.get_state) is not None
        assert (
            MeasurementRasterManageInput(action=MeasurementRasterManageAction.raster_list)
            is not None
        )
        assert TriggerManageInput(action=TriggerManageAction.rule_remove) is not None
        assert RecordingManageInput(action=RecordingManageAction.list_recordings) is not None
        assert DataLoggerManageInput(action=DataLoggerManageAction.list) is not None
