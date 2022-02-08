from ansible.module_utils.dockpulp_common import diff_settings
from ansible.module_utils.dockpulp_common import describe_changes


def test_diff_settings():
    """test diff_settings"""
    settings = {"docker-id": "virt-artifacts-server", "description": "before change"}
    params = {"docker-id": "virt-artifacts-server", "description": "after change"}
    differences = diff_settings(settings, params)
    assert differences == [("description", "before change", "after change")]


def test_diff_settings_none():
    """test diff_settings without difference"""
    settings = {"docker-id": "virt-artifacts-server", "description": "before change"}
    params = {"docker-id": "virt-artifacts-server", "description": "before change"}
    differences = diff_settings(settings, params)
    assert differences == []


def test_describe_changes():
    """test describe_changes"""
    differences = [("description", "before_change", "after_change")]
    result = describe_changes(differences)
    assert result == ["changing description from before_change to after_change"]
