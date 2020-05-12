#!/usr/bin/env python
# coding: utf8
'''
@author: qitan
@contact: qqing_lai@hotmail.com
@file: models.py
@time: 2018/9/16 00:01
@desc:
'''

from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os, time


class FileStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.rename(os.path.join('./media', name), os.path.join('./media', '{}.save'.format(name)))
        return name
