#!/usr/bin/env python
# coding: utf8
'''
@author: qitan
@contact: qqing_lai@hotmail.com
@file: soms_lib.py
@time: 2018/9/06 00:25
@desc:
'''

from __future__ import unicode_literals

from django.contrib.auth import get_user_model


def get_token(length):
    new_token = get_user_model().objects.make_random_password(length=length,
                                                              allowed_chars='abcdefghjklmnpqrstuvwxyABCDEFGHJKLMNPQRSTUVWXY3456789')
    return new_token

