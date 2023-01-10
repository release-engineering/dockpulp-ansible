import subprocess
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dockpulp_common import diff_settings, describe_changes


ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "honeybadger",
}


DOCUMENTATION = '''
---
module: dockpulp_repo

short_description: Create and update dockpulp repositories in Docker Pulp server
description:
- Create and update CDN repositories within Red Hat's Docker Pulp server.
options:
   env:
     description:
       - The environment to run dock-pulp command, which is configured in /etc/dockpulp.conf
       - "Example: stage"
   dockpulp_user:
       - The user to login to docker pulp server
   dockpulp_password:
     description:
       - The password to login to docker pulp server
   repo_name:
     description:
       - Pulp repo label.
       - "Example: rhceph-4-rhel8"
     required: true
   namespace:
     description:
       - Use like the 'product-line' value in release engineering documentation.
         Final value will have redhat prepended where necessary. This entry will
         be used for the following
       - "Example: rhceph"
     required: true
   content_url:
     description:
       - the path for content of dockpulp repo. It need to start with '/content' and end
         with $repo_name. It is not required if redirect-url = no in /etc/dockpulp.conf,
         but we still make it required in this module.
       - "Example: /content/dist/containers/rhel8/multiarch/containers/redhat-rhceph-rhceph-4-rhel8"
     required: true
   description:
     description:
       - a description for the dockpulp repo
       - "Example: This operator is responsible for maintaining the kubevirt components
         needed for scheduling, scale and performance of VMs. Such as: VM templates and
         related infrastructure, metrics collectors, node feature discovery plugins, scheduler
         extensions and anything related to those."
     required: true
   distribution:
     description:
       - The distribution of this dockpulp repo
       - "Example: tech-preview"
     choices: [ga, tech-preview, tech-preview, beta]
     required: true
requirements:
  - "python >= 3.6"
  - "lxml"
  - "requests-gssapi"
'''

EXAMPLES = '''
- name: create dockpulp repositories on rhel8
  hosts: localhost
  tasks:
  - name: Add rhceph-4-tools-for-rhel-8-x86_64-rpms cdn repo
    dockpulp_repo:
      env: stage
      dockpulp_user: fakeuser
      dockpulp_password: fakeuserPassw0rd
      repo_name: rhceph-4-rhel8
      namespace: rhceph
      content_url: /content/dist/containers/rhel8/multiarch/containers/redhat-rhceph-rhceph-4-rhel8
      description: This is a test repo for create dockpulp repo
      distribution: ga
- name: create dockpulp repositories on rhel9
  hosts: localhost
  tasks:
  - name: Add rhceph-4-tools-for-rhel-9-x86_64-rpms cdn repo
    dockpulp_repo:
      env: stage
      dockpulp_user: fakeuser
      dockpulp_password: fakeuserPassw0rd
      repo_name: rhceph-4-rhel9
      namespace: rhceph
      content_url: /content/dist/containers/rhel9/multiarch/containers/redhat-rhceph-rhceph-4-rhel9
      description: This is a test repo for create dockpulp repo
      distribution: ga
'''

DOCK_PULP_TIMEOUT = 120

UPDATE_MAP = {
    "description": "--description",
    "title": "--title",
    "docker-id": "--dockerid",
    "distribution": "--distribution",
}

LOGGED_IN = {
    "qa": False,
    "stage": False,
    "prod": False,
}

COMPARABLES = ["description", "title", "docker-id", "distribution"]


def login(env, dockpulp_user, dockpulp_password, timeout=DOCK_PULP_TIMEOUT):
    """Login to docker pulp
    Args:
        env: The environment to log in to
        timeout: Maximum number of seconds to wait for a result (default = 120)
    Returns:
        True if login is successful, False otherwise
        stdout when the command is executed
    """
    command = [
        "dock-pulp",
        "-d",
        "--server",
        env,
        "login",
        "-u",
        dockpulp_user,
        "-p",
        dockpulp_password,
    ]
    if LOGGED_IN[env]:
        return LOGGED_IN[env], ""

    returncode, stdout = execute_command(command, timeout)
    if returncode == 0:
        LOGGED_IN[env] = True
    return LOGGED_IN[env], stdout


def execute_command(command, timeout=DOCK_PULP_TIMEOUT):
    """Execute a given command using the subprocess module
    Args:
        command (list): List of args for a command
        timeout: Maximum number of seconds to wait for a result
    Returns:
        The CompletedProcess object from running the command
    """
    # Attempting dock-pulp command with args
    # In python39, we use subprocess.run
    # To support py27, we use subprocess.Popen
    result = subprocess.Popen(
        command,
        encoding="utf8",
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    outs, errs = result.communicate(timeout=timeout)
    return result.poll(), outs + errs


def create_command(env, dockpulp_repo):
    """Build the command to create the repos based on the
    current environment.
    Args:
        server: The environment to use
        component (dict): The dockpulp repo to create
    Returns:
        The command required to create dock-pulp repository
    """
    repo_name = dockpulp_repo.get("repo_name")
    distribution = dockpulp_repo.get("distribution")
    description = dockpulp_repo.get("description")
    namespace = dockpulp_repo.get("namespace")
    content_url = dockpulp_repo.get("content_url")

    command = [
        "dock-pulp",
        "--server",
        env,
        "create",
        namespace,
        repo_name,
        content_url,
        "--description=%s" % description,
        "--distribution=%s" % distribution,
    ]
    return command


def update_command(env, full_name, differences):
    """Build the command to update a given repo
    based on which fields need to be modified
    Args:
        server: Environment to run command on
        full_name: the full repo name
        modified (dict): A dictionary of changes
    Returns:
        The command to update an existing repository
    """
    command = [
        "dock-pulp",
        "--server",
        env,
        "update",
        full_name,
    ]
    # Modified is in the form [('key', 'current_value', 'new_value')]
    for key, _, new_value in differences:
        line = "%s=%s" % (UPDATE_MAP.get(key), new_value)
        command.append(line)
    return command


def get_comparable_repo(repo):
    """Get a subset of comparable data from a repo.
    HB can only change certain values so it's important to only compare those.
    Args:
        repo (dict): The repo to pull comparable values from
    Returns:
        A subset of the repo dict with only comparable values
    """
    if not repo:
        return repo
    return {key: value for key, value in repo.items() if key in COMPARABLES}


def update_dockpulp_repo(env, full_repo_name, differences):
    command = update_command(env, full_repo_name, differences)
    _, stdout = execute_command(command)
    returncode = 0 if "updating repo %s" % full_repo_name in stdout else 1
    return returncode


def create_dockpulp_repo(env, dockpulp_repo):
    command = create_command(env, dockpulp_repo)
    returncode, stdout = execute_command(command)
    return returncode


def parse_output(output):
    """Parse the output of a dock-pulp command
    Args:
        output (str): The output of the dock-pulp command
    Returns:
        A dictionary with the results parsed
    Example:
        {'title': 'repo-name', 'distribution': 'ga'}
    """
    values = {}
    lines = output.split("\n")
    for line in lines:
        if "=" in line:
            parsed = line.strip("INFO").strip().split(" = ")
            values[parsed[0]] = parsed[1]

    return values


def get_existing_repo(
    full_repo_name, env, dockpulp_user, dockpulp_password, timeout=DOCK_PULP_TIMEOUT
):
    """Check that a Docker Pulp repo exists. If it does, return the result.
    Args:
        full_repo_name: the full name of the repo to check
        server: 'stage', 'prod', 'qa'
        timeout: maximum number of seconds allowed for the command to execute
    Returns:
        A dictonary representing the repo or None if it does not exist
    """
    login_succeed, stdout = login(env, dockpulp_user, dockpulp_password)
    if not login_succeed:
        raise RuntimeError("Error logging into dock-pulp: %s" % stdout)

    command = ["dock-pulp", "-d", "--server", env, "list", "-d", full_repo_name]
    returncode, stdout = execute_command(command)

    if returncode != 0:
        return None

    return parse_output(stdout)


def prepare_diff_data(dockpulp_repo, repo):
    """Prepare diff data for result.
    Args:
        dockpulp_repo (dict): dockpulp repo from dockpulp server
        repo (dict): Repo specified via module params
    Returns:
        A dictonary for comparing the existing repo and params
    """
    if dockpulp_repo:
        before_header = dockpulp_repo["docker-id"]
        after_header = repo["docker-id"]
    else:
        before_header = "Not present"
        after_header = "New container repository %s" % repo["docker-id"]

        # Need to use an empty dict instead of None otherwise
        # ansible's built-in diff callback will throw errors
        # trying to call splitlines() on it
        dockpulp_repo = {}

    return {
        "before_header": before_header,
        "after_header": after_header,
        "before": dockpulp_repo,
        "after": repo,
    }


def ensure_dockpulp_repo(params, check_mode=True):
    """Ensure that this CDN repo exists in the Docker pulp server.
    Args:
        param params({}): The dockpulp repo to create
        check_mode (bool): describe what would happen, but don't do it.
    Returns:
        A dictonary for ansible result
    """
    result = {"returncode": 0, "changed": False, "stdout_lines": []}
    env = params.get("env")
    dockpulp_user = params.get("dockpulp_user")
    dockpulp_password = params.get("dockpulp_password")
    login_succeed, stdout = login(env, dockpulp_user, dockpulp_password)
    if not login_succeed:
        raise RuntimeError("Error logging into dock-pulp: %s" % stdout)

    # The only fields that are possible to change are distribution and description
    # Only way for others to change would be repo name or namepsace change
    # which would lead to a new repo created anyways
    repo_name = params.get("repo_name")
    namespace = params.get("namespace")
    description = params.get("description")
    distribution = params.get("distribution")
    full_repo_name = "redhat-%s-%s" % (namespace, repo_name)
    new_repo = {
        "description": description,
        "title": full_repo_name,
        "docker-id": "%s/%s" % (namespace, repo_name),
        "distribution": distribution,
    }
    # Get a comparable existing one
    old_repo = get_comparable_repo(
        get_existing_repo(full_repo_name, env, dockpulp_user, dockpulp_password)
    )
    if old_repo:
        differences = diff_settings(old_repo, new_repo)

    # Repo exists and have same params, no need to update
    if old_repo and not differences:
        # Repo for %s already exists - skipping
        return result

    # Dockpulp repo exists but need update
    if old_repo and differences:
        result["changed"] = True
        changes = describe_changes(differences)
        result["stdout_lines"].extend(changes)
        result["diff"] = prepare_diff_data(old_repo, new_repo)
        if not check_mode:
            returncode = update_dockpulp_repo(env, full_repo_name, differences)
            result["returncode"] = returncode
        return result

    # Dockpulp repo doesn't exist, create a new dockpulp repo
    if not old_repo:
        result["changed"] = True
        result["stdout_lines"] = ["Created %s" % full_repo_name]
        result["diff"] = prepare_diff_data(old_repo, new_repo)
        if not check_mode:
            new_repo_params = {
                "description": description,
                "repo_name": repo_name,
                "namespace": namespace,
                "distribution": distribution,
            }
            returncode = create_dockpulp_repo(env, new_repo_params)
            result["returncode"] = returncode
        return result


def run_module():
    module_args = dict(
        env=dict(required=True),
        dockpulp_user=dict(required=True),
        dockpulp_password=dict(required=True, no_log=True),
        repo_name=dict(required=True),
        namespace=dict(required=True),
        content_url=dict(required=True),
        description=dict(required=True),
        distribution=dict(required=True),
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    check_mode = module.check_mode
    params = module.params

    repo_name = params["repo_name"]
    content_url = params["content_url"]
    if not content_url.startswith("/content"):
        module.fail_json(
            msg="the content-url needs to start with /content",
            changed=False,
            rc=1,
        )
    if not content_url.rstrip("/").endswith(repo_name):
        module.fail_json(
            msg="the content-url needs to end with %s" % repo_name,
            changed=False,
            rc=1,
        )

    try:
        result = ensure_dockpulp_repo(params, check_mode)
    except RuntimeError as e:
        module.fail_json(msg=str(e), changed=False, rc=1)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
