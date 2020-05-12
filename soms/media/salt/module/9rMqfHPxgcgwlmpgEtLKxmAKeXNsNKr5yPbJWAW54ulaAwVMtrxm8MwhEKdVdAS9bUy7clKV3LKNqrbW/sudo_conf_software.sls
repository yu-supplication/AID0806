/etc/sudoers: 
  file.append:
    - text:
      - "software    ALL=(ALL)NOPASSWD:ALL"
