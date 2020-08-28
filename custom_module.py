#!/usr/bin/python

DOCUMENTATION = """
---
module: custom_module.py
short_description: Pass provided data to remote service
description:
  - Mention anything useful for your workmate.
  - Also mention anything you want to remember in 6 months.
options:
  user:
    description:
      - user to identify to remote service
  password:
    description:
      - password for authentication to remote service
  data:
    description:
      - data to send to remote service
"""

import yaml
from ansible.module_utils.basic import AnsibleModule


def main():
    module_args = dict(
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        data=dict(type='str', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False
    )

    got = {}
    wanted = {}

    # Populate both `got` and `wanted`.
    # [...]

    if got != wanted:
        result['changed'] = True
        result['diff'] = dict(
            before=yaml.safe_dump(got),
            after=yaml.safe_dump(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    # Apply changes.
    # [...]

    module.exit_json(**result)


if __name__ == '__main__':
    main()
