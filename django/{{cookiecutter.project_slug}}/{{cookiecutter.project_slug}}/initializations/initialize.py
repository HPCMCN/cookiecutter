# -*- coding: utf-8 -*-
# author: HPCM
# time: 2024/3/5 15:13
# file: initialize.py
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password


# ==== 迁移初始化 ============================================================
def set_first_user():
    def create_first_user(apps, schema_editor):
        """创建首个用户"""
        logging.info("Create first user!")
        model = get_user_model()
        username = "admin"
        password = "123123"
        user = model.objects.filter(username=username).first()
        if not user:
            user = model()
            user.username = username
            user.mobile = "11111111111"
            user.name = "第一个用户"
            user.is_staff = 1
            user.is_superuser = True
        user.password = make_password(password)
        user.save()
        logging.warning(f"\n    username: {username}\n    password: {password}\nMust save it!")

    return create_first_user
