Install from Ansible Galaxy
---------------------------

We distribute dockpulp-ansible through the `Ansible Galaxy
<https://galaxy.ansible.com/release_engineering/dockpulp_ansible>`_.

If you are using Ansible 2.9 or greater, you can `install
<https://docs.ansible.com/ansible/latest/user_guide/collections_using.html>`_
dockpulp_ansible like:

  ansible-galaxy collection install release_engineering.dockpulp_ansible

This will install the latest Git snapshot automatically. Use ``--force``
upgrade your installed version to the latest version.


dockpulp_repo
--------------

The ``dockpulp_repo`` module can create, update dockpulp repo on dockpulp server. The env running
the playbook need to have dock-pulp installed

pip3 install --no-deps git+https://github.com/release-engineering/dockpulp.git@dockpulp-1.67-1

and three configuration files for dockpulp server

* dockpulp.conf

* dockpulpdistributions.json

* dockpulpdistributors.json


The playbook.yml file is a small playbook that simply loads our module:

.. code-block:: yaml

  - name: create dockpulp repositories on rhel9
    hosts: localhost
    collections:
      - release_engineering.dockpulp_ansible
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

Next
----
