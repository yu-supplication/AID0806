websphere:
  group.present:
    - name: websphere
    - gid: 1004
  user.present:
    - shell: /bin/bash
    - home: /home/websphere
    - uid: 1004
    - gid: 1004
    - password: '$1$12345678$RWi6xzYuoNi1Lh7vo34qw1'
