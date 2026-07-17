"""Unit tests for sources.models.tooldecrator.metainfo."""

from sources.models.tooldecorator.metainfo import (
    AnnotationInfo,
    MetaInfo,
    ToolDomain,
    ToolGroup,
)


class TestAnnotationInfo:
    def test_defaults(self):
        ann = AnnotationInfo()
        assert ann == {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }

    def test_all_overridden(self):
        ann = AnnotationInfo(read_only=False, destructive=True, idempotent=False, open_world=True)
        assert ann == {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        }

    def test_read_only_false(self):
        ann = AnnotationInfo(read_only=False)
        assert ann["readOnlyHint"] is False
        assert ann["destructiveHint"] is False
        assert ann["idempotentHint"] is True
        assert ann["openWorldHint"] is False

    def test_destructive_and_not_idempotent(self):
        ann = AnnotationInfo(read_only=False, destructive=True, idempotent=False)
        assert ann["readOnlyHint"] is False
        assert ann["destructiveHint"] is True
        assert ann["idempotentHint"] is False

    def test_is_dict(self):
        ann = AnnotationInfo()
        assert isinstance(ann, dict)

    def test_contains_all_four_keys(self):
        ann = AnnotationInfo()
        assert set(ann.keys()) == {
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        }


class TestMetaInfo:
    def test_application_lifecycle(self):
        meta = MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE)
        assert meta == {"domain": "application", "group": "lifecycle"}

    def test_variable_read(self):
        meta = MetaInfo(ToolDomain.VARIABLE, ToolGroup.READ)
        assert meta == {"domain": "variable", "group": "read"}

    def test_variable_write(self):
        meta = MetaInfo(ToolDomain.VARIABLE, ToolGroup.WRITE)
        assert meta == {"domain": "variable", "group": "write"}

    def test_calibration_page_management(self):
        meta = MetaInfo(ToolDomain.CALIBRATION, ToolGroup.PAGE_MANAGEMENT)
        assert meta == {"domain": "calibration", "group": "page_management"}

    def test_tool_window_window_management(self):
        meta = MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT)
        assert meta == {"domain": "tool_window", "group": "window_management"}

    def test_is_dict(self):
        meta = MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT)
        assert isinstance(meta, dict)

    def test_contains_domain_and_group_keys(self):
        meta = MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING)
        assert set(meta.keys()) == {"domain", "group"}


class TestToolDomain:
    def test_all_values_are_strings(self):
        for member in ToolDomain:
            assert isinstance(member.value, str)

    def test_expected_domains(self):
        values = {m.value for m in ToolDomain}
        expected = {
            "application",
            "bus_logging",
            "bus_monitor",
            "bus_replay",
            "calibration",
            "measurement",
            "platform",
            "project",
            "recorder",
            "tool_window",
            "variable",
        }
        assert expected.issubset(values)

    def test_is_str_subclass(self):
        assert issubclass(ToolDomain, str)


class TestToolGroup:
    def test_all_values_are_strings(self):
        for member in ToolGroup:
            assert isinstance(member.value, str)

    def test_expected_groups(self):
        values = {m.value for m in ToolGroup}
        expected = {
            "lifecycle",
            "window_management",
            "logger_management",
            "filter_management",
            "monitor_management",
            "replay_management",
            "online_calibration",
            "page_management",
            "proposed_calibration",
            "signal_management",
            "recording",
            "data_export",
            "bookmarks",
            "raster_management",
            "triggers",
            "data_logging",
            "connectivity",
            "variable_descriptions",
            "hardware",
            "discovery",
            "configuration",
            "project_roots",
            "experiment_management",
            "project_management",
            "recorder_management",
            "read",
            "write",
        }
        assert expected.issubset(values)

    def test_is_str_subclass(self):
        assert issubclass(ToolGroup, str)
