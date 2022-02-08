# dockpulp-ansible
========================
This is only a draft, need to be tested.

dockpulp_repo
--------------

The ``dockpulp_repo`` module can create, update, dockpulp repo on dockpulp server. The env running
the playbook need to have dock-pulp installed

pip3 install --no-deps git+https://github.com/release-engineering/dockpulp.git@dockpulp-1.67-1

and three configuration files for dockpulp server
*dockpulp.conf
*dockpulpdistributions.json
*dockpulpdistributors.json

.. code-block:: yaml

    - name: create dockpulp repositories on rhel9
      hosts: localhost
      tasks:
      - name: Add rhceph-4-tools-for-rhel-9-x86_64-rpms cdn repo
        dockpulp_repo:
          env: stage
          dockpulp_user: fakeuser
          dockpulp_password: fakeuserPassw0rd
          repo_name: rhceph-4-rhel8
          namespace: rhceph
          platform: rhel9
          description: This is a test repo for create dockpulp repo
          distribution: ga
