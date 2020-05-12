/etc/sudoers: 
  file.append:
    - text:
      - "oracle    ALL=(ALL)NOPASSWD:ALL"
