#!/usr/bin/env python
# coding: utf8
'''
@author: qitan
@contact: qqing_lai@hotmail.com
@file: models.py
@time: 2017/3/30 15:30
@desc:
'''

from __future__ import unicode_literals

# from django.contrib.auth.models import User
from userauth.models import User, UserGroup, Department
from django.db import models
from django.utils import timezone

from deploy.storage import FileStorage
from deploy.soms_lib import get_token


def user_dir_path(instance, filename):
    # if instance.visible == 0:
    #    return 'salt/module/user_{user_id}/{filename}'.format(user_id=instance.user.id, filename=filename)
    if instance.visible == 0:
        return '/opt/SOMS-master/soms/media/salt/module/group_{group_id}/{filename}'.format(group_id=instance.user_group.id, filename=filename)
    else:
        return '/opt/SOMS-master/soms/media/salt/module/public/{filename}'.format(filename=filename)


def file_upload_dir_path(instance, filename):
    return '/opt/SOMS-master/soms/media/salt/fileupload/user_{user_id}/{file_tag}/{filename}'.format(
        user_id=instance.user.id, file_tag=instance.file_tag, filename=filename)


# Create your models here.


class SaltHost(models.Model):
    hostname = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=u'主机名称')
    # salt主机存活状态
    alive = models.BooleanField(default=False, verbose_name=u'连通状态')
    # 上次检测时间
    alive_time_last = models.DateTimeField(auto_now=True)
    # 当前检测时间
    alive_time_now = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False, verbose_name=u'是否加入salt管理')
    user_group = models.ManyToManyField(UserGroup, related_name='host_usergroup_set', verbose_name=u'所属用户组')
    department = models.ManyToManyField(Department, related_name='host_department_set', verbose_name=u'所属部门')

    def __str__(self):
        return self.hostname

    class Meta:
        default_permissions = ()
        permissions = (
            ("view_deploy", u"查看主机部署"),
            ("edit_deploy", u"管理主机部署"),
            ("edit_salthost", u"管理Salt主机")
        )
        verbose_name = u'Salt主机授权'
        verbose_name_plural = u'Salt主机授权管理'


class SaltGroup(models.Model):
    # 定义分组别名
    nickname = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=u'Salt分组')
    # 分组后groupname不可变
    groupname = models.CharField(
        max_length=80,
        unique=True)
    minions = models.ManyToManyField(
        SaltHost,
        related_name='salt_host_set',
        verbose_name=u'Salt主机')
    user_group = models.ManyToManyField(UserGroup, related_name='group_usergroup_set', verbose_name=u'所属用户组')
    department = models.ManyToManyField(Department, blank=True, related_name='saltgroup_department_set',
                                        verbose_name=u'所属部门')

    def __str__(self):
        return self.nickname

    class Meta:
        default_permissions = ()
        permissions = (
            ("edit_saltgroup", u"管理Salt主机分组"),
        )
        verbose_name = u'Salt分组'
        verbose_name_plural = u'Salt分组管理'


class ModuleAttchment(models.Model):
    attchment = models.FileField(upload_to='salt/module/{}'.format(get_token(80)), null=True, blank=True,
                                 verbose_name=u'模块上传', storage=FileStorage())
    upload_time = models.DateTimeField(default=timezone.now, verbose_name=u'上传时间')

    def __unicode__(self):
        return self.attchment.name

    class Meta:
        default_permissions = ()


class ModuleUpload(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=50, unique=True, verbose_name=u'模块名称')
    module = models.CharField(max_length=50, verbose_name=u'调用模块')
    module_path = models.CharField(max_length=255, null=True, blank=True, verbose_name=u'模块路径')
    attchment = models.ManyToManyField(ModuleAttchment, related_name='module_attchment', verbose_name=u'模块上传')
    # {0:公共，1：相应用户组}
    visible = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'可见等级')
    user_group = models.ManyToManyField(UserGroup, blank=True, null=True, related_name='module_usergroup_set',
                                        verbose_name=u'所属用户组')
    created_time = models.DateTimeField(default=timezone.now, verbose_name=u'创建时间')
    modify_time = models.DateTimeField(auto_now=True, verbose_name=u'修改时间')
    remark = models.CharField(max_length=255, blank=True, verbose_name=u'备注')

    def __str__(self):
        return self.name

    class Meta:
        default_permissions = ()
        permissions = (
            ("edit_module", u"管理Salt模块"),
        )
        verbose_name = u'Salt模块'
        verbose_name_plural = u'Salt模块管理'


class FileUpload(models.Model):
    user = models.ForeignKey(User)
    target = models.CharField(max_length=244, verbose_name=u'远程主机')
    file_path = models.FileField(
        upload_to=file_upload_dir_path,
        verbose_name=u'文件上传')
    remote_path = models.CharField(max_length=244, verbose_name=u'远程路径')
    file_tag = models.CharField(
        max_length=244,
        unique=True,
        verbose_name=u'文件标签')
    remark = models.TextField(max_length=50, blank=True, verbose_name=u'备注')

    def __str__(self):
        return self.file_path

    class Meta:
        default_permissions = ()
        permissions = (
            ("view_filemanage", u"查看文件管理"),
            ("edit_fileupload", u"管理文件上传"),
            ("edit_filedownload", u"管理文件下载"),
        )
        verbose_name = u'文件上传'
        verbose_name_plural = u'文件上传管理'


class FileRollback(models.Model):
    user = models.ForeignKey(User)
    target = models.CharField(
        max_length=244,
        default=None,
        verbose_name=u'远程主机')
    cur_path = models.CharField(max_length=244)
    bak_path = models.CharField(max_length=244)
    file_tag = models.CharField(max_length=244, verbose_name=u'文件标签')
    remark = models.TextField(max_length=50, blank=True, verbose_name=u'备注')
    is_group = models.BooleanField(default=False)

    def __unicode__(self):
        return self.target

    class Meta:
        default_permissions = ()
        ordering = ['-id']
        verbose_name = u'文件备份'
        verbose_name_plural = u'文件备份管理'


class Project(models.Model):
    user = models.ForeignKey(User)
    pname = models.CharField(max_length=255, unique=True, verbose_name=u'项目名称')
    name = models.CharField(max_length=255, unique=True, verbose_name=u'项目')
    src = models.CharField(max_length=255, verbose_name=u'源地址')
    src_user = models.CharField(max_length=80, default=None, blank=True, null=True, verbose_name=u'源用户')
    src_passwd = models.CharField(max_length=255, default=None, blank=True, null=True, verbose_name=u'源密码')
    path = models.CharField(max_length=255, verbose_name=u'项目路径')
    process = models.CharField(max_length=255, default=None, blank=True, null=True, verbose_name=u'项目进程')
    salt_test = models.CharField(max_length=255, default=None, blank=True, null=True, verbose_name=u'测试环境')
    salt_group = models.CharField(max_length=255, verbose_name=u'正式环境')
    user_group = models.ForeignKey(UserGroup, default=None, blank=True, null=True, related_name='project_usergroup_set',
                                   verbose_name=u'用户组')

    def __unicode__(self):
        return self.pname

    class Meta:
        default_permissions = ()
        permissions = (
            ('view_project', u'查看项目'),
            ('edit_project', u'管理项目')
        )
        ordering = ['-id']
        verbose_name = u'项目'
        verbose_name_plural = u'项目管理'


class ProjectRollback(models.Model):
    name = models.ForeignKey(Project)
    tag = models.CharField(max_length=100, verbose_name=u'标签')
    env = models.CharField(max_length=1, verbose_name=u'发布环境')

    def __unicode__(self):
        return self.tag

    class Meta:
        default_permissions = ()
        ordering = ['-id']

class UpdateHostInfo(models.Model):
    nodename = models.CharField(max_length=50, unique=True, default=None, verbose_name=u'Salt主机')
    hostname = models.CharField(max_length=50, verbose_name=u'主机名')
    manufacturer = models.CharField(max_length=20, blank=True, verbose_name=u'厂商')
    productname = models.CharField(max_length=100, blank=True, verbose_name=u'型号')
    sn = models.CharField(max_length=200, blank=True, verbose_name=u'序列号')
    cpu_model = models.CharField(max_length=100, blank=True, verbose_name=u'CPU型号')
    cpu_nums = models.PositiveSmallIntegerField(verbose_name=u'CPU线程')
    memory = models.CharField(max_length=20, verbose_name=u'内存')
    disk = models.TextField(blank=True, verbose_name=u'硬盘')
    network = models.TextField(blank=True, verbose_name=u'网络接口')
    os = models.CharField(max_length=200, blank=True, verbose_name=u'操作系统')
    virtual = models.CharField(max_length=20, blank=True, verbose_name=u'虚拟化')
    kernel = models.CharField(max_length=200, blank=True, verbose_name=u'内核')
    shell = models.CharField(max_length=10, blank=True, verbose_name=u'Shell')
    zmqversion = models.CharField(max_length=10, blank=True, verbose_name=u'ZeroMQ')
    saltversion = models.CharField(max_length=10, blank=True, verbose_name=u'Salt版本')
    locale = models.CharField(max_length=200, blank=True, verbose_name=u'编码')
    selinux = models.CharField(max_length=50, blank=True, verbose_name=u'Selinux')
    idc = models.CharField(max_length=50, blank=True, verbose_name=u'机房')
    networkarea = models.CharField(max_length=50, blank=True, verbose_name=u'区域')
    

    def __unicode__(self):
        return self.hostname
    
    class Meta:
        default_permissions = ()
        permissions = (
            ("view_asset", u"查看资产"),
            ("edit_asset", u"管理资产"),
        )
        verbose_name = u'主机资产信息'
        verbose_name_plural = u'主机资产信息管理'

class FilesUpload(models.Model):
    files_name = models.CharField(max_length=200, verbose_name=u'文件名')
    files_path = models.CharField(max_length=200, verbose_name=u'文件路径')
    commonly_used_variables = models.CharField(max_length=200, verbose_name=u'常用变量')
    

    def __unicode__(self):
        return self.files_name
    
    class Meta:
        default_permissions = ()
        permissions = (
            ("view_asset", u"部署管理"),
            ("edit_asset", u"部署管理"),
        )
        verbose_name = u'远程脚本'
        verbose_name_plural = u'脚本文件信息'