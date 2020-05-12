{% set files = salt['pillar.get']('files',) %}
{% set dst_path = salt['pillar.get']('dst_path',) %}
{% set src_path = salt['pillar.get']('src_path',) %}
{% set remote_path = salt['pillar.get']('remote_path',) %}

backup_dir:
  file.directory:
    - name: {{ dst_path }}
    - makedirs: True

file_upload:
  file.recurse:
    - name: {{ remote_path }}
    - source: salt://fileupload/user_1/{{ src_path }}

