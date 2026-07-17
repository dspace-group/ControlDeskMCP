"""Unit tests for sources/utils/pagination.py."""

from sources.utils.pagination import paginate


def test_flat_list_first_page():
    items = list(range(10))
    result = paginate(items, offset=0, limit=5, list_key="items")
    assert result["items"] == [0, 1, 2, 3, 4]
    assert result["total_count"] == 10
    assert result["has_more"] is True
    assert result["next_offset"] == 5
    assert "pagination_hint" in result
    assert "offset=5" in result["pagination_hint"]
    assert "5 of 10" in result["pagination_hint"]


def test_flat_list_last_page():
    items = list(range(10))
    result = paginate(items, offset=8, limit=5, list_key="items")
    assert result["items"] == [8, 9]
    assert result["total_count"] == 10
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert "pagination_hint" not in result


def test_flat_list_exact_page():
    items = list(range(10))
    result = paginate(items, offset=5, limit=5, list_key="items")
    assert result["items"] == [5, 6, 7, 8, 9]
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert "pagination_hint" not in result


def test_flat_list_empty():
    result = paginate([], offset=0, limit=10, list_key="items")
    assert result["items"] == []
    assert result["total_count"] == 0
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert "pagination_hint" not in result


def test_flat_list_custom_key():
    items = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    result = paginate(items, offset=1, limit=1, list_key="monitors")
    assert result["monitors"] == [{"name": "b"}]
    assert result["total_count"] == 3
    assert result["has_more"] is True
    assert result["next_offset"] == 2
    assert "pagination_hint" in result
    assert "offset=2" in result["pagination_hint"]


def test_dict_with_list_key_first_page():
    data = {"loggers": [{"id": i} for i in range(8)], "extra": "meta"}
    result = paginate(data, offset=0, limit=3, list_key="loggers")
    assert result["loggers"] == [{"id": 0}, {"id": 1}, {"id": 2}]
    assert result["extra"] == "meta"
    assert result["total_count"] == 8
    assert result["has_more"] is True
    assert result["next_offset"] == 3
    assert "pagination_hint" in result
    assert "3 of 8" in result["pagination_hint"]
    assert "offset=3" in result["pagination_hint"]


def test_dict_with_list_key_second_page():
    data = {"loggers": [{"id": i} for i in range(8)]}
    result = paginate(data, offset=3, limit=3, list_key="loggers")
    assert result["loggers"] == [{"id": 3}, {"id": 4}, {"id": 5}]
    assert result["has_more"] is True
    assert result["next_offset"] == 6
    assert "pagination_hint" in result
    assert "offset=6" in result["pagination_hint"]


def test_dict_with_list_key_no_more():
    data = {"signals": ["a", "b", "c"]}
    result = paginate(data, offset=0, limit=10, list_key="signals")
    assert result["signals"] == ["a", "b", "c"]
    assert result["has_more"] is False
    assert result["next_offset"] is None
    assert "pagination_hint" not in result


def test_dict_missing_list_key():
    data = {"other": "data"}
    result = paginate(data, offset=0, limit=10, list_key="signals")
    assert result["signals"] == []
    assert result["total_count"] == 0
    assert result["has_more"] is False
    assert "pagination_hint" not in result


def test_dict_is_not_mutated():
    data = {"items": [1, 2, 3]}
    original_copy = list(data["items"])
    paginate(data, offset=0, limit=2, list_key="items")
    assert data["items"] == original_copy


def test_pagination_hint_offset_range_in_message():
    items = list(range(20))
    result = paginate(items, offset=5, limit=5, list_key="items")
    assert result["has_more"] is True
    assert "offset 5" in result["pagination_hint"]
    assert "9" in result["pagination_hint"]


def test_no_hint_when_single_page():
    items = [1, 2, 3]
    result = paginate(items, offset=0, limit=200, list_key="items")
    assert result["has_more"] is False
    assert "pagination_hint" not in result
