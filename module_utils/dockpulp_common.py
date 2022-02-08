def diff_settings(settings, params):
    """Diff the "live" settings against our Ansible parameters.
    Args:
        settings (dict): settings for a Product, or Product Version, etc.
        params (dict): settings from our Ansible playbook.
    Returns:
        a list of three-element tuples:
            1. the key that has changed
            2. the old value
            3. the new value
    """
    differences = []
    for key in params:
        current_value = settings.get(key)
        new_value = params[key]
        if current_value != new_value:
            differences.append((key, current_value, new_value))
    return differences


def describe_changes(changes):
    """Human-readable changes suitable for stdout_lines
    Args:
    changes (list): list of three-element tuples: "key", "old value",
                         "new value" (see diff_settings())
    """
    tmpl = "changing {} from {} to {}"
    return [tmpl.format(*change) for change in changes]
