weblogic:
  group.present:
    - name: weblogic
    - gid: 1003
  user.present:
    - shell: /bin/bash
    - home: /home/weblogic
    - uid: 1003
    - gid: 1003
    - password: '$1$12345678$AIjCkC8XtJzwCPzY0Xzec/'
