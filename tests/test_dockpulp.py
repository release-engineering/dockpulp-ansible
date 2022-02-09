from unittest import TestCase
from utils import patch

import pytest
import dockpulp_repo
from utils import AnsibleExitJson, AnsibleFailJson, exit_json, fail_json, set_module_args


class TestSetupDockpulp(TestCase):
    def setUp(self):
        self.dockpulp_repo_params = {
            "repo_name": "virt-artifacts-server-rhel8",
            "namespace": "namespace-test",
            "distribution": "ga",
            "description": "virt-artifacts-server contains different builds of virtctl.",
            "env": "qa",
            "content_url": "/content/redhat-namespace-test-virt-artifacts-server-rhel8",
            "dockpulp_user": "dockpulp_user",
            "dockpulp_password": "dockpulp_Passw0rd",
        }
        self.out = "FIRST LINE\nINFO     property = value\nINFO     oh = wow\n"
        dockpulp_repo.LOGGED_IN["qa"] = False

    @pytest.fixture(autouse=True)
    def fake_exits(self, monkeypatch):
        monkeypatch.setattr(dockpulp_repo.AnsibleModule, "exit_json", exit_json)
        monkeypatch.setattr(dockpulp_repo.AnsibleModule, "fail_json", fail_json)

    @patch("dockpulp_repo.execute_command")
    def test_login_ok(self, mock_ec):
        """Test login function"""
        mock_ec.return_value = (0, "logged in")
        dockpulp_repo.login("qa", "dockpulp_user", "dockpulp_Passw0rd", 120)
        mock_ec.assert_called_once_with(
            [
                "dock-pulp",
                "-d",
                "--server",
                "qa",
                "login",
                "-u",
                "dockpulp_user",
                "-p",
                "dockpulp_Passw0rd",
            ],
            120,
        )

    @patch("dockpulp_repo.execute_command")
    def test_login_unsuccessful(self, mock_ec):
        """Test failed login function"""
        mock_ec.return_value = (-1, "failed")
        result = dockpulp_repo.login("qa", "dockpulp_user", "dockpulp_Passw0rd")[0]
        self.assertEqual(result, False)

    def test_login_already(self):
        """Test if login has already happened"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        result = dockpulp_repo.login("qa", "dockpulp_user", "dockpulp_Passw0rd")[0]
        self.assertEqual(result, True)

    @patch("dockpulp_repo.subprocess.Popen")
    def test_execute_command(self, mock_run):
        """Test execute_command"""
        mock_run.return_value.communicate.return_value = ("succeed", "")
        mock_run.return_value.poll.return_value = 0
        result, _ = dockpulp_repo.execute_command(["fake", "command"], 120)
        self.assertEqual(result, 0)

    def test_parse_output(self):
        """Test parse_output properly parses output"""
        expected = {"property": "value", "oh": "wow"}
        result = dockpulp_repo.parse_output(self.out)
        self.assertDictEqual(result, expected)

    @patch("dockpulp_repo.execute_command")
    @patch("dockpulp_repo.parse_output")
    def test_existing_repo(self, mock_parse_output, mock_ec):
        """Test existing_repo finds existing repo"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        mock_ec.return_value = (0, "found one repo")
        dockpulp_repo.get_existing_repo("repo", "qa", "dockpulp_user", "dockpulp_Passw0rd")
        mock_parse_output.assert_called()

    @patch("dockpulp_repo.execute_command")
    def test_existing_repo_nologin(self, mock_ec):
        """Test existing_repo with failed login"""
        mock_ec.return_value = (-1, "not logged in")
        with pytest.raises(RuntimeError):
            dockpulp_repo.get_existing_repo("repo", "qa", "dockpulp_user", "dockpulp_passw0rd")

    @patch("dockpulp_repo.execute_command")
    def test_existing_repo_notfound(self, mock_ec):
        """Test existing_repo handles non-existent repo"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        mock_ec.return_value = (-1, "not found")
        result = dockpulp_repo.get_existing_repo("repo", "qa", "dockpulp_user", "dockpulp_passw0rd")
        expected = None
        self.assertEqual(result, expected)

    def test_create_commmand(self):
        """Test that create_command assembles command correctly"""
        env = "qa"
        repo = {
            "repo_name": "test-repo",
            "description": "fake description",
            "distribution": "tech-preview",
            "namespace": "redhat-namespace",
            "content_url": "/content/containers/redhat-redhat-namespace-test-repo",
        }
        expected_command = [
            "dock-pulp",
            "--server",
            env,
            "create",
            "redhat-namespace",
            "test-repo",
            "/content/containers/redhat-redhat-namespace-test-repo",
            "--description=fake description",
            "--distribution=tech-preview",
        ]
        result = dockpulp_repo.create_command(env, repo)
        self.assertEqual(result, expected_command)

    def test_update_commmand(self):
        """Test that update_command assembles command correctly"""
        server = "server"
        repo_name = "redhat-namespace-repo-name-rhelver"
        modified = [
            ("description", "current_description", "new_description"),
            ("title", "current_title", "new_title"),
            ("distribution", "current_distribution", "new_distribution"),
            ("docker-id", "current_id", "new_id"),
        ]
        expected_command = [
            "dock-pulp",
            "--server",
            server,
            "update",
            repo_name,
            "--description=new_description",
            "--title=new_title",
            "--distribution=new_distribution",
            "--dockerid=new_id",
        ]
        result = dockpulp_repo.update_command(server, repo_name, modified)
        self.assertEqual(result, expected_command)

    def test_get_comparable_repo(self):
        """Test get_comparable_repo only returns a comparable repo"""
        repo = {
            "blah": "blah",
            "extra": "extra",
            "description": "d",
            "docker-id": "di",
            "title": "title",
            "distribution": "dist",
            "more": "fake-data",
        }
        expected = {
            "description": "d",
            "docker-id": "di",
            "title": "title",
            "distribution": "dist",
        }
        result = dockpulp_repo.get_comparable_repo(repo)
        self.assertEqual(result, expected)

    def test_get_comparable_repo_none(self):
        """Test get_comparable_repo handles None repo"""
        self.assertEqual(dockpulp_repo.get_comparable_repo(None), None)

    @patch("dockpulp_repo.execute_command")
    def test_ensure_dockpulp_repo_nologin(self, mock_ec):
        """Test ensure_dockpulp_repo with failed login"""
        mock_ec.return_value = (-1, "not logged in")
        with pytest.raises(RuntimeError):
            dockpulp_repo.ensure_dockpulp_repo(self.dockpulp_repo_params, True)

    def test_prepare_diff_data(self):
        """test prepare_diff_data"""
        dock_repo = {
            "description": "d",
            "docker-id": "di",
            "title": "title",
            "distribution": "dist",
        }
        repo = {
            "description": "changed",
            "docker-id": "di",
            "title": "title",
            "distribution": "dist",
        }
        expected = {
            "before_header": "di",
            "after_header": "di",
            "before": {
                "description": "d",
                "docker-id": "di",
                "title": "title",
                "distribution": "dist",
            },
            "after": {
                "description": "changed",
                "docker-id": "di",
                "title": "title",
                "distribution": "dist",
            },
        }
        result = dockpulp_repo.prepare_diff_data(dock_repo, repo)
        self.assertEqual(result, expected)

    def test_prepare_diff_data_none(self):
        """test prepare_diff_data without any change"""
        repo = {
            "description": "changed",
            "docker-id": "container-native-virtualization-virt-artifacts-server",
            "title": "title",
            "distribution": "dist",
        }
        expected = {
            "before_header": "Not present",
            "after_header": "New container repository"
            + " container-native-virtualization-virt-artifacts-server",
            "before": {},
            "after": {
                "description": "changed",
                "docker-id": "container-native-virtualization-virt-artifacts-server",
                "title": "title",
                "distribution": "dist",
            },
        }
        result = dockpulp_repo.prepare_diff_data(None, repo)
        self.assertEqual(result, expected)

    @patch("dockpulp_repo.execute_command")
    def test_update_dockpulp_repo(self, mock_ec):
        """test update_dockpulp_repo can update repo"""
        stdout = "INFO    updating repo redhat-namespace-test-virt"
        mock_ec.return_value = (0, stdout)
        result = dockpulp_repo.update_dockpulp_repo(
            "qa", "redhat-namespace-test-virt", [("description", "before_change", "after_change")]
        )
        assert result == 0

    @patch("dockpulp_repo.execute_command")
    def test_create_dockpulp_repo(self, mock_ec):
        """test create_dockpulp_repo can create repo"""
        repo = {
            "description": "changed",
            "docker-id": "container-native-virtualization-virt-artifacts-server",
            "title": "title",
            "distribution": "dist",
        }
        mock_ec.return_value = (0, "created")
        result = dockpulp_repo.create_dockpulp_repo("qa", repo)
        assert result == 0

    @patch("dockpulp_repo.get_comparable_repo")
    @patch("dockpulp_repo.execute_command")
    def test_ensure_dockpulp_repo_unchanged_run(self, mock_ec, mock_cmp_repo):
        """Test ensure_dockpulp_repo without repo change"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        mock_ec.return_value = (0, "no change")
        mock_cmp_repo.return_value = {
            "description": "virt-artifacts-server contains different builds of virtctl.",
            "title": "redhat-namespace-test-virt-artifacts-server-rhel8",
            "docker-id": "namespace-test/virt-artifacts-server-rhel8",
            "distribution": "ga",
        }
        check_mode = False
        result = dockpulp_repo.ensure_dockpulp_repo(self.dockpulp_repo_params, check_mode)
        assert result == {"returncode": 0, "changed": False, "stdout_lines": []}

    @patch("dockpulp_repo.get_comparable_repo")
    @patch("dockpulp_repo.update_dockpulp_repo")
    @patch("dockpulp_repo.execute_command")
    def test_ensure_dockpulp_repo_update(self, mock_ec, mock_update_dockpulp_repo, mock_cmp_repo):
        """Test ensure_dockpulp_repo when updating an existing repo"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        mock_ec.return_value = (0, "succeed")
        mock_update_dockpulp_repo.return_value = 0
        mock_cmp_repo.return_value = {
            "description": "virt-artifacts-server",
            "title": "redhat-namespace-test-virt-artifacts-server-rhel8",
            "docker-id": "namespace-test/virt-artifacts-server-rhel8",
        }
        check_mode = False
        result = dockpulp_repo.ensure_dockpulp_repo(self.dockpulp_repo_params, check_mode)
        expected = {
            "returncode": 0,
            "changed": True,
            "stdout_lines": [
                "changing description from virt-artifacts-server to virt-artifacts-server"
                + " contains different builds of virtctl.",
                "changing distribution from None to ga",
            ],
            "diff": {
                "before_header": "namespace-test/virt-artifacts-server-rhel8",
                "after_header": "namespace-test/virt-artifacts-server-rhel8",
                "before": {
                    "description": "virt-artifacts-server",
                    "title": "redhat-namespace-test-virt-artifacts-server-rhel8",
                    "docker-id": "namespace-test/virt-artifacts-server-rhel8",
                },
                "after": {
                    "description": "virt-artifacts-server contains different builds of virtctl.",
                    "title": "redhat-namespace-test-virt-artifacts-server-rhel8",
                    "docker-id": "namespace-test/virt-artifacts-server-rhel8",
                    "distribution": "ga",
                },
            },
        }
        assert result["returncode"] == expected["returncode"]
        assert result["changed"] == expected["changed"]
        assert result["diff"] == expected["diff"]
        assert result["stdout_lines"].sort() == expected["stdout_lines"].sort()

    @patch("dockpulp_repo.create_dockpulp_repo")
    @patch("dockpulp_repo.get_comparable_repo")
    @patch("dockpulp_repo.execute_command")
    def test_ensure_dockpulp_repo_new(self, mock_ec, mock_cmp_repo, mock_cdp):
        """Test ensure_dockpulp_repo when creating new repo"""
        dockpulp_repo.LOGGED_IN["qa"] = True
        mock_cmp_repo.return_value = None
        mock_ec.return_value = (0, "succeed")
        mock_cdp.return_value = 0
        check_mode = False
        result = dockpulp_repo.ensure_dockpulp_repo(self.dockpulp_repo_params, check_mode)
        expected = {
            "returncode": 0,
            "changed": True,
            "stdout_lines": ["Created redhat-namespace-test-virt-artifacts-server-rhel8"],
            "diff": {
                "before_header": "Not present",
                "after_header": "New container repository"
                + " namespace-test/virt-artifacts-server-rhel8",
                "after": {
                    "description": "virt-artifacts-server contains different builds of virtctl.",
                    "title": "redhat-namespace-test-virt-artifacts-server-rhel8",
                    "docker-id": "namespace-test/virt-artifacts-server-rhel8",
                    "distribution": "ga",
                },
                "before": {},
            },
        }
        assert result == expected

    @patch("dockpulp_repo.ensure_dockpulp_repo")
    def test_main_ok(self, mock_edr):
        """Test dockpulp_repo module when it succeeds"""
        set_module_args(self.dockpulp_repo_params)
        mock_edr.return_value = {"returncode": 0, "changed": True, "stdout_lines": []}
        with pytest.raises(AnsibleExitJson) as ex:
            dockpulp_repo.main()
        result = ex.value.args[0]
        assert result["changed"] is True

    @patch("dockpulp_repo.execute_command")
    def test_main_fail(self, mock_ec):
        """Test dockpulp_repo module when it fails"""
        mock_ec.return_value = (-1, "failed")
        set_module_args(self.dockpulp_repo_params)
        dockpulp_repo.LOGGED_IN["qa"] = False
        with pytest.raises(AnsibleFailJson) as ex:
            dockpulp_repo.main()
        result = ex.value.args[0]
        assert result["msg"] == "Error logging into dock-pulp: failed"
