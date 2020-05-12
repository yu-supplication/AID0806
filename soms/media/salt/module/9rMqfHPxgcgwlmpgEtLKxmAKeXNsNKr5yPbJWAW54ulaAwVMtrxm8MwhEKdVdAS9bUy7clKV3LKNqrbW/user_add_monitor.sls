monitor:
  group.present:
    - name: monitor
    - gid: 1001
  user.present:
    - shell: /bin/bash
    - home: /home/monitor
    - uid: 1001
    - gid: 1001
    - password: '$1$12345678$ooaQ1n8FVBWP8rKRORwrl/'
