/etc/sudoers: 
  file.append:
    - text:
      - "weblogic    ALL=(ALL)NOPASSWD:ALL"
