#!/usr/bin/python

DOCUMENTATION = """
---
module: iosxr_sshkeys.py
short_description: Copy and enable SSH keys to IOSXR device
description:
  - This module copy the provided SSH keys and attach them to the users.
  - The users are expected to already exist in the running configuration.
  - Users not listed in this module will have their SSH keys removed.
options:
  keys:
    description:
      - dictionary mapping users to their SSH keys in OpenSSH format
"""

import yaml
import textfsm
import io
import subprocess
import base64
import binascii
import tempfile

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.iosxr.plugins.module_utils.network.iosxr.iosxr import (
    copy_file,
    get_connection,
    run_commands,
)


def ssh2cisco(sshkey):
    """Convert a public key in OpenSSH format to the format expected by
    Cisco."""
    proc = subprocess.run(["ssh-keygen", "-f", "/dev/stdin", "-e", "-mPKCS8"],
                          input=sshkey.encode('ascii'),
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"unable to convert key: {sshkey}")
    decoded = base64.b64decode("".join(proc.stdout.decode(
        'ascii').split("\n")[1:-2]))
    return binascii.hexlify(decoded).decode('ascii').upper()


def main():
    module_args = dict(
        keys=dict(type='dict', elements='str', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    result = dict(
        changed=False
    )

    # Get existing keys
    command = "show crypto key authentication rsa all"
    out = run_commands(module, command)

    # Parse keys

    # Key label: vincent
    # Type     : RSA public key authentication
    # Size     : 2048
    # Imported : 16:17:08 UTC Tue Aug 11 2020
    # Data     :
    #  30820122 300D0609 2A864886 F70D0101 01050003 82010F00 3082010A 02820101
    #  00D81E5B A73D82F3 77B1E4B5 949FB245 60FB9167 7CD03AB7 ADDE7AFE A0B83174
    #  A33EC0E6 1C887E02 2338367A 8A1DB0CE 0C3FBC51 15723AEB 07F301A4 B1A9961A
    #  2D00DBBD 2ABFC831 B0B25932 05B3BC30 B9514EA1 3DC22CBD DDCA6F02 026DBBB6
    #  EE3CFADA AFA86F52 CAE7620D 17C3582B 4422D24F D68698A5 52ED1E9E 8E41F062
    #  7DE81015 F33AD486 C14D0BB1 68C65259 F9FD8A37 8DE52ED0 7B36E005 8C58516B
    #  7EA6C29A EEE0833B 42714618 50B3FFAC 15DBE3EF 8DA5D337 68DAECB9 904DE520
    #  2D627CEA 67E6434F E974CF6D 952AB2AB F074FBA3 3FB9B9CC A0CD0ADC 6E0CDB2A
    #  6A1CFEBA E97AF5A9 1FE41F6C 92E1F522 673E1A5F 69C68E11 4A13C0F3 0FFC782D
    #  27020301 0001

    out = out[0].replace(' \n', '\n')
    template = r"""
Value Required Label (\w+)
Value Required,List Data ([A-F0-9 ]+)

Start
 ^Key label: ${Label}
 ^Data\s+: -> GetData

GetData
 ^ ${Data}
 ^$$ -> Record Start
""".lstrip()
    re_table = textfsm.TextFSM(io.StringIO(template))
    got = {data[0]: "".join(data[1]).replace(' ', '')
           for data in re_table.ParseText(out)}

    # Check what we want
    wanted = {k: ssh2cisco(v)
              for k, v in module.params['keys'].items()}

    if got != wanted:
        result['changed'] = True
        result['diff'] = dict(
            before=yaml.safe_dump(got),
            after=yaml.safe_dump(wanted)
        )

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    # Copy changed or missing SSH keys
    conn = get_connection(module)
    for user in wanted:
        if user not in got or wanted[user] != got[user]:
            dst = f"/harddisk:/publickey_{user}.raw"
            with tempfile.NamedTemporaryFile() as src:
                decoded = base64.b64decode(
                    module.params['keys'][user].split()[1])
                src.write(decoded)
                src.flush()
                copy_file(module, src.name, dst)
        command = ("admin crypto key import authentication rsa "
                   f"username {user} {dst}")
        conn.send_command(command, prompt="yes/no", answer="yes")

    # Remove unwanted users
    for user in got:
        if user not in wanted:
            command = ("admin crypto key zeroize authentication rsa "
                       f"username {user}")
            conn.send_command(command, prompt="yes/no", answer="yes")

    module.exit_json(**result)


if __name__ == '__main__':
    main()
