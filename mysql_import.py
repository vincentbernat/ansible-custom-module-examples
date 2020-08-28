#!/usr/bin/python

DOCUMENTATION = """
---
module: mysql_import.py
short_description: Update MySQL database with SQL instructions
options:
  sql:
    description:
      - SQL statements to execute
  user:
    description:
      - username to connect to MySQL
  password:
    description:
      - password to connect to MySQL
  database:
    description:
      - database to use
  tables:
    required: true
    description:
      - list of tables which will be modified

"""

import yaml
import pymysql

from ansible.module_utils.basic import AnsibleModule


def main():
    module_args = dict(
        sql=dict(type='str', required=True),
        user=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        database=dict(type='str', required=True),
        tables=dict(type='list', required=True, elements='str'),
    )

    result = dict(
        changed=False
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    got = {}
    wanted = {}
    tables = module.params['tables']
    sql = module.params['sql']
    statements = [statement.strip()
                  for statement in sql.split(";\n")
                  if statement.strip()]

    connection = pymysql.connect(user=module.params['user'],
                                 password=module.params['password'],
                                 db=module.params['database'],
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute("SELECT * FROM {}".format(table))
            got[table] = cursor.fetchall()

    with connection.cursor() as cursor:
        for statement in statements:
            try:
                cursor.execute(statement)
            except pymysql.OperationalError as err:
                code, message = err.args
                result['msg'] = "MySQL error for {}: {}".format(
                    statement,
                    message)
                module.fail_json(**result)
        for table in tables:
            cursor.execute("SELECT * FROM {}".format(table))
            wanted[table] = cursor.fetchall()

    if got != wanted:
        result['changed'] = True
        result['diff'] = [dict(
            before_header=table,
            after_header=table,
            before=yaml.safe_dump(got[table]),
            after=yaml.safe_dump(wanted[table]))
                          for table in tables
                          if got[table] != wanted[table]]

    if module.check_mode or not result['changed']:
        module.exit_json(**result)

    connection.commit()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
