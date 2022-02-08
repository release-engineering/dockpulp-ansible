import sys
from os.path import abspath, dirname, join

from ansible.module_utils.six import PY2, PY3


def pytest_sessionstart(session):
    """
    This pytest hook gets executed after the Session object has been created
    and before any collection starts.

    ansible-playbook will automatically load modules from the "library"
    directory. To mimic this during tests, we will prepend the absolute path
    of the ``library`` directory, so we can import modules during testing.

    ansible-playbook will also import files from the "module_utils" directory
    into the "ansible.module_utils.*" namespace
    """
    working_directory = dirname(abspath((__file__)))
    library_path = join(dirname(working_directory), "library")
    if library_path not in sys.path:
        sys.path.insert(0, library_path)

    module_utils_path = join(dirname(working_directory), "module_utils")

    dockpulp_location = join(module_utils_path, "dockpulp_common.py")
    dockpulp_module_name = "ansible.module_utils.dockpulp_common"

    if PY3:
        # Python 3.5+
        import importlib.util

        dockpulp_spec = importlib.util.spec_from_file_location(
            dockpulp_module_name, dockpulp_location
        )
        dockpulp_module = importlib.util.module_from_spec(dockpulp_spec)
        dockpulp_spec.loader.exec_module(dockpulp_module)
    if PY2:
        import imp

        dockpulp_module = imp.load_source(dockpulp_module_name, dockpulp_location)

    sys.modules[dockpulp_module_name] = dockpulp_module

    import ansible.module_utils

    ansible.module_utils.dockpulp_common = dockpulp_module
