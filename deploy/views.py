#!/usr/bin/env python
# coding: utf8
'''
@author: qitan
@contact: qqing_lai@hotmail.com
@file: views.py
@time: 2017/3/30 15:28
@desc:
'''

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse, JsonResponse

from django.http import StreamingHttpResponse

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views import View

from deploy.saltapi import SaltAPI
from soms import settings
from userperm.views import UserIP
from userperm.models import *
from .models import *
from .forms import *
# custom function
from tar_file import make_tar
from md5 import md5sum

try:
    import json
except ImportError:
    import simplejson as json

import time
import datetime
import shutil
import os
import re
import tarfile, zipfile
from ruamel import yaml


# Create your views here.

def module_deal(module):
    module = module.split('/')
    return '.'.join(module[2:-1])


def dict_p(dict_a):
    r = ''
    iftrue = 0
    temp = []
    if isinstance(dict_a, dict):
        for k in dict_a.keys():
            if k == 'name':
                dict_a.pop(k)
                continue
            if k == 'result' and not k:
                temp.append(1)
            else:
                temp.append(0)
            v = dict_a[k]
            if isinstance(v, dict):
                dict_p(v)
            else:
                r = r + k + ': ' + str(v) + '<br />'
    if 1 in temp:
        iftrue = 1
    return {'result': r, 'iftrue': iftrue}


def list_dict(d):
    s = {}
    result = []
    for k, v in d.items():
        ret = {}
        for m, n in v.items():
            temp = dict_p(n)
            s[m] = temp['result']
            ret['iftrue'] = temp['iftrue']
        ret[k] = s
        result.append(ret)
    return result


class UploadFile(View):
    def get(self, request):
        pass

    def post(self, request):
        form = AttchmentForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            tmp = form.save()
            file = os.path.join('media/', tmp.attchment.name)
            ext = os.path.splitext(file)[1]
            tmp.save()
            data = {'is_valid': True, 'name': os.path.basename(file), 'url': tmp.attchment.url,
                    'id': tmp.pk}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)


def ProjectExec(sapi, tgt_list, fun, arg, tgt_type):
    '''
    定义项目进程管理
    :param sapi:
    :param tgt_list:
    :param fun:
    :param arg:
    :param tgt_type:
    :return:
    '''
    jid = sapi.remote_execution(tgt_list, fun, arg + ';echo ":::"$?', tgt_type)
    s = SaltGroup.objects.get(groupname=tgt_list)
    s_len = s.minions.all().count()
    ret = ''
    rst = {}
    while (len(rst) < s_len):
        rst = sapi.salt_runner(jid)
        # time.sleep(1)
    for k in rst:
        ret = ret + u'主机：<span style="color:#e6db74">' + k + '</span><br />运行结果：<br />%s<br />' % rst[k]
        r = rst[k].split(':::')[-1].strip()
        if r != '0':
            ret = ret + '<span style="color:#f92672">%s</span> 执行失败！<br />' % arg + '<br />'
        else:
            ret = ret + '<span style="color:#e6db74">%s</span> 执行成功！<br />' % arg + '<br />'
    return {u'进程管理': {'result': ret}}


def RemoteExec(request, fun, group=False):
    '''
    定义远程命令函数
    '''
    command_list = [j.command.split(',') for i in request.user.group.all() for j in i.command.filter(is_allow=True)]
    command_list = [j for i in command_list for j in i]
    check = 2
    is_group = False
    ret = ''
    temp_dict = {}
    result = []
    jid = ''
    arg = ''
    if request.method == 'POST':
        if request.is_ajax():
            if request.POST.get('check_type') == 'panel-group':
                grp = request.POST.get('tgt_select')
                tgt_list = SaltGroup.objects.get(nickname=grp).groupname
                tgt_type = 'nodegroup'
                is_group = True
            else:
                tgt_select = request.POST.getlist('tgt_select[]')
                if not tgt_select:
                    tgt_list = request.POST.get('tgt_select')
                else:
                    tgt_list = ','.join(tgt_select)
                tgt_type = 'list'
            if fun == 'cmd.run':
                arg = request.POST.get('arg').strip(' ')
            else:
                arg = request.POST.get('arg')
                module = ModuleUpload.objects.get(pk=arg)
                if module.visible == 0:
                    arg = 'module.user_%s.%s' % (module.user.pk, module.module)
                elif module.visible == 2:
                    arg = 'module.public.%s' % module.module
                else:
                    arg = 'module.group_%s.%s' % (module.user_group.pk, module.module)
            if is_group:
                s = SaltGroup.objects.get(groupname=tgt_list)
                s_len = s.minions.all().count()
            else:
                s = tgt_list.split(',')
                s_len = len(s)

            sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                           password=settings.SALT_API['password'])
            try:
                ## 远程命令
                if fun == 'cmd.run':
                    if arg in command_list and not request.user.is_superuser:
                        sret = {'CRITICAL': '不能执行此命令，老大会不高兴滴...', 'iftrue': 2}
                        result.append(sret)
                    elif not arg or not tgt_list:
                        check = 1
                        sret = {'WARNING': '未选择主机或未输入命令...', 'iftrue': 1}
                        result.append(sret)
                    else:
                        is_danger = []
                        for command in command_list:
                            for j in command.split(' '):
                                if j == arg:
                                    is_danger.append(1)
                        if is_danger and not request.user.is_superuser:
                            sret = {'CRITICAL': '不能执行此命令，老大会不高兴滴...', 'iftrue': 2}
                            result.append(sret)
                        else:
                            jid = sapi.remote_execution(tgt_list, fun, arg + ';echo ":::"$?', tgt_type)
                            rst = {}
                            t = 0
                            r = None
                            while (t < 5):
                                rst = sapi.salt_runner(jid)
                                if len(rst) == s_len:
                                    r = True
                                    break
                                t = t + 1
                                # time.sleep(1)
                            if r:
                                check = 0
                                for k, v in rst.items():
                                    check = v.split(':::')[-1].strip()
                                    result.append({k: v.replace('\n', '<br />'), 'iftrue': int(check)})
                            else:
                                check = 1
                                sret = {'INFO': '请稍候点击[重新查询]或到任务管理中查询结果<jid: %s>...' % jid, 'iftrue': 1}
                                result.append(sret)
                ## 模块部署
                else:
                    jid = sapi.remote_execution(tgt_list, fun, arg, tgt_type)
                    rst = {}
                    t = 0
                    r = None
                    while (t < 3):
                        rst = sapi.salt_runner(jid)
                        if len(rst) == s_len:
                            r = True
                            break
                        t = t + 1
                        # time.sleep(1)
                    if r:
                        check = 0
                        sret = rst
                        result = list_dict(sret)
                    else:
                        check = 1
                        sret = {'INFO': {'消息': '请稍候点击[重新查询]或到任务管理中查询结果<jid: %s>...' % jid}, 'iftrue': 1}
                        result.append(sret)
                    if not arg or not tgt_list:
                        check = 1
                        sret = {'WARNING': {'警告': '未选择主机或未输入命令...'}, 'iftrue': 1}
                        result.append(sret)
                temp_dict['result'] = result
                temp_dict['jid'] = jid
            except:
                pass

    return {'result': result, 'sret': temp_dict, 'arg': arg, 'jid': jid, 'check': check, 'is_group': is_group}


def AjaxResult(jid, result_type, check_type):
    '''
    定义ajax查询结果函数
    '''

    sret = {}
    sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                   password=settings.SALT_API['password'])
    rtype = '远程命令'
    result = ''
    t = 0
    r = None
    while (t < 3):
        rst = sapi.salt_runner(jid)
        if rst:
            r = True
            break
        t = t + 1
        # time.sleep(1)

    if check_type == 'deploy':
        rtype = '模块部署'
        if r:
            sret = rst
            sret = list_dict(sret)
        else:
            sret = {'INFO': {'消息': '请稍候重新查询...'}}
        try:
            for k, v in sret.items():
                result = result + '主机：' + k + '<br /><p class="mydashed">结果：<br />'
                for m, n in v.items():
                    result = result + m + '<br />' + n
                result = result + "</p>"
        except:
            result = 'Err'
    else:
        if r:
            for k, v in rst.items():
                sret[k] = v.replace('\n', '<br />')
        else:
            sret = {'INFO': '请稍候重新查询...'}
        for k, v in sret.items():
            result = result + '主机：' + k + '<br /><p class="mydashed">结果：<br />' + v + '</p>'
    try:
        # 记录查询操作日志
        message = get_object_or_404(Message, action=jid)
        m = re.search('\[([^:]*)\]', message.content)
        arg = m.groups()[0]
        message.content = '%s：[%s]<br />原始输出：<br />%s' % (rtype, arg, result)
        message.audit_time = datetime.datetime.now()
        message.save()
    except:
        pass

    # if result_type == '1':
    return sret
    # else:
    #    return rst_all


@login_required
def salt_key_list(request):
    '''
    salt主机列表
    '''

    if request.user.is_superuser:
        minions = SaltHost.objects.filter(status=True)
        minions_pre = SaltHost.objects.filter(status=False)
        return render(request, 'salt_key_list.html', {'all_minions': minions, 'all_minions_pre': minions_pre})
    else:
        raise Http404


@login_required
def salt_key_import(request):
    '''
    导入salt主机
    '''
    if request.user.is_superuser:
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        minions, minions_pre = sapi.list_all_key()
        alive = False
        ret_alive = sapi.salt_alive('*')
        for node_name in minions:
            try:
                alive = ret_alive[node_name]
                alive = True
            except:
                alive = False
            try:
                SaltHost.objects.create(hostname=node_name, alive=alive, status=True)
            except:
                salthost = SaltHost.objects.get(hostname=node_name)
                now = datetime.datetime.now()
                alive_old = SaltHost.objects.get(hostname=node_name).alive
                if alive != alive_old:
                    salthost.alive_time_last = now
                    salthost.alive = alive
                salthost.alive_time_now = now
                salthost.save()
        for node_name in minions_pre:
            try:
                SaltHost.objects.get_or_create(hostname=node_name, alive=alive, status=False)
            except:
                print 'not create'

        return redirect('key_list')
    else:
        raise Http404


@login_required
def salt_key_manage(request, hostname=None):
    '''
    接受或拒绝salt主机，同时更新数据库
    '''
    if request.user.is_superuser:
        if request.method == 'GET':
            sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                           password=settings.SALT_API['password'])
            hostname = request.GET.get('hostname')
            salthost = SaltHost.objects.get(hostname=hostname)
            action = ''

            if request.GET.has_key('add'):
                ret = sapi.accept_key(hostname)
                if ret:
                    salthost.status = True
                    salthost.save()
                    result = 3
                    action = u'添加主机'
            if request.GET.has_key('delete'):
                ret = sapi.delete_key(hostname)
                if ret:
                    salthost.status = False
                    salthost.save()
                    result = 2
                    action = u'删除主机'
            if request.GET.has_key('flush') and request.is_ajax():
                # result: 0 在线 | 1 离线
                result = {'retcode': 1}
                ret = sapi.salt_alive(hostname)
                try:
                    alive = ret[hostname]
                    if alive:
                        result = {'retcode': 0}
                except:
                    pass
                    # alive = False
                salthost.alive = alive
                salthost.save()
                action = u'刷新主机'
                if action:
                    Message.objects.create(type=u'部署管理', user=request.user.first_name, action=action,
                                           action_ip=UserIP(request),
                                           content=u'%s %s' % (action, salthost.hostname))
                return JsonResponse(result)

            if action:
                Message.objects.create(type=u'部署管理', user=request.user.first_name, action=action,
                                       action_ip=UserIP(request), content=u'%s %s' % (action, salthost.hostname))

        return redirect('key_list')
    else:
        raise Http404


@login_required
def salt_group_list(request):
    '''
    salt主机分组列表
    '''

    if request.user.is_superuser:
        groups = SaltGroup.objects.all()
        return render(request, 'salt_group_list.html', {'all_groups': groups})
    else:
        raise Http404


@login_required
def salt_group_manage(request, id=None):
    '''
    salt主机分组管理，同时更新salt-master配置文件
    '''
    if request.user.is_superuser:
        action = ''
        page_name = ''
        if id:
            group = get_object_or_404(SaltGroup, pk=id)
            action = 'edit'
            page_name = '编辑分组'
        else:
            group = SaltGroup()
            action = 'add'
            page_name = '新增分组'

        if request.method == 'GET':
            if request.GET.has_key('delete'):
                id = request.GET.get('id')
                group = get_object_or_404(SaltGroup, pk=id)
                group.delete()
                Message.objects.create(type=u'部署管理', user=request.user.first_name, action=u'删除分组',
                                       action_ip=UserIP(request), content='删除分组 %s' % group.nickname)
                try:
                    with open('/opt/SOMS-master/soms/saltconfig/nodegroup.conf', 'r') as f:
                        content = yaml.load(f, Loader=yaml.RoundTripLoader)

                    del content['nodegroups'][group.groupname]

                    with open('/opt/SOMS-master/soms/saltconfig/nodegroup.conf', 'w') as f:
                        if not content['nodegroups']:
                            f.truncate()
                        else:
                            yaml.round_trip_dump(content, f, default_flow_style=False, allow_unicode=True, indent=2,
                                                 block_seq_indent=2)
                except:
                    pass
                return redirect('group_list')

        if request.method == 'POST' and request.is_ajax:
            minions = request.POST.getlist('minions[]')
            nickname = request.POST.get('nickname')
            groupname = request.POST.get('groupname')

            group.nickname = nickname
            if action == 'add':
                group.groupname = groupname

            try:
                group.save()
            except Exception, e:
                print e
                return JsonResponse({'retcode': 1, 'msg': str(e)})

            group.minions.clear()
            group.minions.add(*minions)

            Message.objects.create(type=u'部署管理', user=request.user.first_name, action=page_name,
                                   action_ip=UserIP(request), content='%s %s' % (page_name, group.nickname))

            minions_l = [i.hostname for i in group.minions.all()]

            content = {'nodegroups': {}}
            try:
                with open('/opt/SOMS-master/soms/saltconfig/nodegroup.conf', 'r') as f:
                    content = yaml.load(f, Loader=yaml.RoundTripLoader)
            except:
                pass

            if not content:
                content = {'nodegroups': {}}
            content['nodegroups'].update({group.groupname: minions_l})

            with open('/opt/SOMS-master/soms/saltconfig/nodegroup.conf', 'w') as f:
                yaml.round_trip_dump(content, f, default_flow_style=False, allow_unicode=True, indent=2,
                                     block_seq_indent=2)

            ## 重新启动salt-api
            import subprocess
            subprocess.Popen('systemctl restart salt-api || /etc/init.d/salt-api restart', shell=True)

            return JsonResponse({'retcode': 0})

        return render(request, 'salt_group_manage.html',
                      {'action': action, 'page_name': page_name, 'group': group, 'aid': id})
    else:
        raise Http404


@login_required
def salt_module_list(request):
    '''
    模块列表
    '''
    if request.user.has_perm('deploy.view_deploy'):
        if request.user.is_superuser:
            module_list = ModuleUpload.objects.all()
        else:
            # 获取用户创建或公开模块
            module_visible_list = [{'pk': i.pk, 'name': i.name, 'module': i.module, 'remark': i.remark, 'user': i.user}
                                   for i in ModuleUpload.objects.filter(Q(user=request.user) | Q(visible=2))]
            # 获取用户组模块
            module_user_group_list = [
                {'pk': i.pk, 'name': i.name, 'module': i.module, 'remark': i.remark, 'user': i.user}
                for g in User.objects.get(pk=request.user.pk).group.all() for i in
                ModuleUpload.objects.filter(user_group=g)]
            # 合并list
            module_list = module_visible_list + [i for i in module_user_group_list if i not in module_visible_list]
        return render(request, 'salt_module_list.html', {'modules': module_list})
    else:
        raise Http404


@login_required
def salt_module_manage(request, id=None):
    '''
    模块管理
    '''
    if request.user.has_perms(['deploy.view_deploy', 'deploy.edit_module']):
        ret = ''
        upload_stat = True
        if id:
            module = get_object_or_404(ModuleUpload, pk=id)
            if request.user.pk != module.user.pk and not request.user.is_superuser:
                return HttpResponse("Not Allowed!")
            action = 'edit'
            page_name = '编辑模块'
        else:
            module = ModuleUpload()
            module_info = {'name': '', 'module': '', 'attchment': '', 'visible': '', 'remark': ''}
            action = 'add'
            page_name = '新增模块'

        if request.method == 'GET':
            if request.GET.has_key('delete'):
                id = request.GET.get('id')
                module = get_object_or_404(ModuleUpload, pk=id)
                if request.user.pk != module.user.pk and not request.user.is_superuser:
                    return HttpResponse("Not Allowed!")
                module.delete()
                Message.objects.create(type=u'部署管理', user=request.user.first_name, action=u'删除模块',
                                       action_ip=UserIP(request), content=u'删除模块 %s' % module.name)

                return redirect('module_list')

        if request.method == 'POST' and request.is_ajax:
            info = request.POST.get('info', None)
            if info:
                module_info = {'name': module.name, 'module': module.module,
                               'attchment': {i.attchment.name.split('/')[-1]: i.attchment.name for i in
                                             module.attchment.all()},
                               'user_group_select': {i.pk: i.group_name for i in module.user_group.all()},
                               'user_group': {i['pk']: i['group_name'] for i in
                                              User.objects.get(pk=request.user.pk).group.values('pk', 'group_name')},
                               'visible': module.visible, 'remark': module.remark}
                return JsonResponse(module_info)
            data = request.POST
            name = data.get('name', None)
            module_call = data.get('module', None)
            upload_list = data.getlist('attchment_id', None)
            visible = data.get('visible', None)
            remark = data.get('remark', None)

            if upload_list:
                module_upload = ModuleAttchment.objects.get(pk=upload_list[0])
                module_path = module_deal(module_upload.attchment.name)
                module.module_path = module_path
            module.user = request.user
            module.name = name
            module.module = module_call
            module.visible = visible
            module.remark = remark
            module.save()
            module.attchment.add(*upload_list)
            module.user_group.clear()
            if str(visible) != '0':
                user_group = data.getlist('user_group')
                module.user_group.add(*user_group)

            Message.objects.create(type=u'部署管理', user=request.user.first_name, action=page_name,
                                   action_ip=UserIP(request), content='%s %s' % (page_name, module.name))
            upload_stat = True
            if upload_stat:
                return redirect('module_list')
            else:
                return render(request, 'salt_module_manage.html',
                              {'action': action, 'page_name': page_name, 'ret': ret})
        else:
            form = ModuleForm(instance=module)
        return render(request, 'salt_module_manage.html',
                      {'form': form, 'action': action, 'page_name': page_name, 'ret': ret, 'id': id})
    else:
        raise Http404


@login_required
def salt_group_minions(request):
    '''
    获取不同分组下的主机列表
    '''
    if request.user.has_perms(['deploy.view_deploy']):
        if request.method == 'POST' and request.is_ajax:
            gid = request.POST.get('gid', None)
            minions = SaltGroup.objects.get(pk=gid).minions.all()
            ret = {i.hostname: i.alive for i in minions}
            return JsonResponse(ret)
    else:
        raise Http404


@login_required
def salt_ajax_result(request):
    '''
    ajax方式查询结果
    '''
    if request.user.has_perm('deploy.edit_deploy'):
        if request.method == 'POST':
            check_type = request.POST.get('type', None)
            jid = request.POST.get('jid', None)
            result_type = request.POST.get('result_type', None)
            if request.is_ajax():
                rst_all = AjaxResult(jid, result_type, check_type)

                return HttpResponse(json.dumps(rst_all))
    else:
        raise Http404


@login_required
def salt_remote(request):
    '''
    salt远程命令界面
    '''
    if request.user.has_perm('deploy.view_deploy'):
        return render(request, 'salt_remote_exec.html', {'groups': ['panel-single', 'panel-group']})
    else:
        raise Http404


@login_required
def salt_script(request):
    '''
    salt远程命令界面
    '''
    if request.user.has_perm('deploy.view_deploy'):
        return render(request, 'salt_script_exec.html', {'groups': ['panel-single', 'panel-group']})
    else:
        raise Http404



@login_required
def salt_remote_exec(request):
    '''
    salt远程命令执行
    '''
    if request.is_ajax and request.user.has_perms(['deploy.view_deploy', 'deploy.edit_deploy']):
        result = ''
        tgt_select = request.POST.get('tgt_select')
        check_type = request.POST.get('check_type')
        arg = request.POST.get('arg').strip(' ')
        if check_type == 'panel-single':
            tgt_type = 'list'
        else:
            tgt_type = 'nodegroup'
            tgt_select = SaltGroup.objects.get(pk=tgt_select).groupname
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        jid = sapi.remote_execution(tgt_select, 'cmd.run', arg, tgt_type)
        rst_source = sapi.salt_runner(jid)
        rst = rst_source['info'][0]['Result']

        Message.objects.create(type=u'部署管理', user=request.user.first_name, action='远程命令', action_ip=UserIP(request),
                               content=u'远程命令： [{}]，结果：{}原始输出：{}'.format(arg, rst, rst_source))
        return JsonResponse(rst)
    else:
        raise Http404

@login_required
def salt_remote_shell_exec(request):
    '''
    salt远程脚本执行
    '''
    print '???????????????????????'
    if request.is_ajax and request.user.has_perms(['deploy.view_deploy', 'deploy.edit_deploy']):
        result = ''
        tgt_select = request.POST.get('tgt_select')
        check_type = request.POST.get('check_type')
        arg = request.POST.get('arg').strip(' ')
        esingle = request.POST.get('esingle')

        print 'post获取的数据 tgt_select ： ' + tgt_select
        print 'post获取的数据 check_type ： ' + check_type
        print 'post获取的数据 arg ： ' + arg
        print 'post获取的数据 esingle ： ' + esingle

        arg = FilesUpload.objects.get(files_name=arg).files_path+arg+" "+esingle

        if check_type == 'panel-single':
            tgt_type = 'list'
        else:
            tgt_type = 'nodegroup'
            tgt_select = SaltGroup.objects.get(pk=tgt_select).groupname
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        jid = sapi.remote_execution(tgt_select, 'cmd.run', arg, tgt_type)
        rst_source = sapi.salt_runner(jid)
        rst = rst_source['info'][0]['Result']

        Message.objects.create(type=u'部署管理', user=request.user.first_name, action='远程命令', action_ip=UserIP(request),
                               content=u'远程命令： [{}]，结果：{}原始输出：{}'.format(arg, rst, rst_source))
        return JsonResponse(rst)
    else:
        raise Http404


@login_required
def salt_module_deploy(request):
    '''
    salt模块部署界面
    '''
    if request.user.has_perm('deploy.view_deploy'):
        modules = ModuleUpload.objects.all()
        return render(request, 'salt_module_deploy.html',
                      {'modules': modules, 'groups': ['panel-single', 'panel-group']})
    else:
        raise Http404


@login_required
def salt_ajax_module_deploy(request):
    '''
    salt模块部署
    '''
    if request.user.has_perms(['deploy.view_deploy', 'deploy.edit_deploy']):
        result = ''
        tgt_select = request.POST.get('tgt_select')
        check_type = request.POST.get('check_type')
        arg = request.POST.getlist('arg[]')
        if check_type == 'panel-single':
            tgt_type = 'list'
        else:
            tgt_type = 'nodegroup'
            tgt_select = SaltGroup.objects.get(pk=tgt_select).groupname

        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        module = ModuleUpload.objects.filter(pk=arg[0])[0]
        src = '/'.join(module.module.split('.')[:-1])
        jid = sapi.remote_module(tgt_select, 'state.sls', 'module.{}.{}'.format(module.module_path, module.module),
                                 {'SALTSRC': 'module/{}'.format(module.module_path)}, tgt_type)
        rst_source = sapi.salt_runner(jid)
        rst = rst_source['info'][0]['Result']

        Message.objects.create(type=u'部署管理', user=request.user.first_name, action=jid, action_ip=UserIP(request),
                               content=u'模块部署 [%s]<br />原始输出：<br />%s' % (module, rst))
        return JsonResponse(rst)
    else:
        raise Http404


@login_required
def salt_advanced_manage(request):
    if request.user.has_perms(['deploy.view_deploy']):
        result = []
        if request.method == 'POST':
            if request.user.has_perms(['deploy.view_deploy', 'deploy.edit_deploy']):
                if request.is_ajax():
                    sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                                   password=settings.SALT_API['password'])

                    targets = request.POST
                    for i in range(0, int(targets['level']) + 1):
                        retcode = 0
                        success = True
                        args = targets[str(i) + "[command]"]
                        check = targets[str(i) + "[check]"]
                        check_type = targets["check_type"]

                        if check_type == 'panel-group':
                            tgt_selects = targets.get(str(i) + "[tgt]", None)
                            tgt_selects = SaltGroup.objects.get(pk=tgt_selects).groupname
                            tgt_type = 'nodegroup'
                        else:
                            tgt_selects = targets.getlist(str(i) + "[tgt][]", None)
                            tgt_selects = ','.join(tgt_selects)
                            tgt_type = 'list'
                        try:
                            jid = sapi.remote_execution(tgt_selects, 'cmd.run', args, tgt_type)
                            rst_source = sapi.salt_runner(jid)
                            rst = rst_source['info'][0]['Result']
                            result.append(rst)

                            for k, v in rst.items():
                                retcode = retcode or v['retcode']
                                success = success and v['success']
                            if int(check) == 0:
                                if retcode:
                                    break

                        except:
                            pass
                    try:
                        Message.objects.create(type=u'部署管理', user=request.user.first_name, action=jid,
                                               action_ip=UserIP(request), content=u'高级管理 Test')
                    except:
                        pass

                    return JsonResponse(result, safe=False)
            else:
                raise Http404

        return render(request, 'salt_remote_exec_advance.html', {})
    else:
        raise Http404


@login_required
def salt_file_upload(request):
    '''
    文件上传界面
    '''
    if request.user.has_perm('deploy.view_filemanage'):
        form = SaltFileForm()
        return render(request, 'salt_file_upload.html', {'form': form, 'groups': ['panel-single', 'panel-group']})
    else:
        raise Http404


def remote_cmd(tgt_select, arg, check_type):
    if check_type == 'panel-single':
        tgt_type = 'list'
    else:
        tgt_type = 'nodegroup'
        tgt_select = SaltGroup.objects.get(pk=tgt_select).groupname
    sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                   password=settings.SALT_API['password'])
    jid = sapi.remote_execution(tgt_select, 'cmd.run', arg, tgt_type)
    rst_source = sapi.salt_runner(jid)
    rst = rst_source['info'][0]['Result']
    return rst


@login_required
def salt_file_download(request):
    def file_iterator(file_name, chunk_size=512):
        with open(file_name) as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    if request.user.has_perms(['deploy.view_filemanage']):
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        if request.method == 'POST':
            if request.user.has_perms(['deploy.view_filemanage', 'deploy.edit_filedownload']):
                check_type = request.POST.get('check_type')
                if check_type == 'panel-single':
                    tgt_select = request.POST.get('tgt_select')
                    arg = request.POST.get('arg').strip(' ')
                    ## 如果是目录，则从结果里排除第一行
                    arg = "[ -d {} ] && ls -gGh {}|awk '{{split($1, a, \".\");print a[1],$NF}}'|awk 'NR>1' || ls -gGh {}|awk '{{split($1, a, \".\");print a[1],$NF}}'".format(
                        arg, arg, arg)
                    rst = remote_cmd(tgt_select, arg, check_type)
                    if (len(tgt_select.split(',')) > 1):
                        import collections
                        temp = []
                        for k, v in rst.items():
                            temp.extend(v['return'].split('\n'))
                        temp_list = [i for i, c in collections.Counter(temp).items() if c > 1]
                    else:
                        temp_list = rst[tgt_select]['return'].split('\n')
                    rst = {tgt_select: temp_list}

                    return JsonResponse(rst)
                else:
                    tgt_select = request.POST.get('tgt_select', None)
                    arg = request.POST.get('arg').strip(' ')
                    arg = "[ -d {} ] && ls -gGh {}|awk '{{split($1, a, \".\");print a[1],$NF}}'|awk 'NR>1' || ls -gGh {}|awk '{{split($1, a, \".\");print a[1],$NF}}'".format(
                        arg, arg, arg)
                    rst = remote_cmd(tgt_select, arg, 'panel-group')
                    tgt_len = SaltGroup.objects.get(pk=tgt_select).minions.count()
                    if (tgt_len > 1):
                        import collections
                        temp = []
                        for _, v in rst.items():
                            temp.extend(v['return'].split('\n'))
                        temp_list = [i for i, c in collections.Counter(temp).items() if c >= tgt_len]
                    else:
                        for _, v in rst.items():
                            temp_list = v['return'].split('\n')
                    rst = {tgt_select: temp_list}

                    return JsonResponse(rst)
            else:
                raise Http404
        if request.method == 'GET':
            if request.user.has_perms(['deploy.view_filemanage', 'deploy.edit_filedownload']):
                if request.GET.get('type') == 'download':
                    tgt_select = request.GET.get('tgt_select', None)
                    arg = request.GET.get('arg', None)
                    remote_file = arg
                    check_type = request.GET.get('check_type')
                    if check_type == 'panel-single':
                        tgt_type = 'list'
                        tgt_list = tgt_select.split(',')
                    else:
                        tgt_type = 'nodegroup'
                        sgroup = SaltGroup.objects.get(pk=tgt_select)
                        tgt_select = sgroup.groupname
                        tgt_list = [i.hostname for i in sgroup.minions.all()]
                    ret_bak = sapi.file_bak(tgt_select, 'cp.push', remote_file, tgt_type)
                    if tgt_select == 'localhost':
                        return render(request, 'redirect.html', {})
                    remote_path = os.path.dirname(remote_file)
                    fname = os.path.basename(remote_file)

                    dl_path = '/opt/SOMS-master/soms/media/salt/filedownload/user_%s/%s' % (request.user.id, remote_path.replace('/', '_'))
                    if not os.path.exists(dl_path):
                        os.makedirs(dl_path)
                    random_path = '/opt/SOMS-master/soms/media/salt/.cache/{}'.format(get_token(12))
                    os.makedirs(random_path)
                    for tgt in tgt_list:
                        _path = '/var/cache/salt/master/minions/%s/files/%s' % (tgt, remote_path)
                        shutil.copy2(os.path.join(_path, fname), os.path.join(random_path, '%s-%s' % (tgt, fname)))
                    tar_file = make_tar(fname, random_path, dl_path)
                    shutil.rmtree(random_path)
                    dl_filename = 'attachment;filename="{0}"'.format('%s-%s' % (remote_path, os.path.basename(tar_file)))
                    ret = u'主机：%s\n结果：远程文件 %s 下载成功！' % (tgt_select, remote_file)
                    Message.objects.create(type=u'文件管理', user=request.user.first_name, action=u'文件下载',
                                           action_ip=UserIP(request), content=u'下载文件 \n%s' % ret)
                    response = StreamingHttpResponse(file_iterator(tar_file))
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = dl_filename

                    return response
            else:
                raise Http404
        return render(request, 'salt_file_download.html', {})
    else:
        raise Http404


@login_required
def salt_ajax_file_upload(request):
    '''
    执行文件上传
    '''
    if request.is_ajax():
        check_type = request.POST.get('check_type')
        tgt_select = request.POST.get('tgt_select')
        files_upload = request.FILES.getlist('files_upload', None)
        remote_path = request.POST.get('remote_path', None).strip(' ')
        remark = request.POST.get('remark', None)
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        upload_dir = '/opt/SOMS-master/soms/media/salt/fileupload/user_%s/%s' % (request.user.id, tag)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        for file in files_upload:
            dest = open(os.path.join(upload_dir, file.name), 'wb+')
            for chunk in file.chunks():
                dest.write(chunk)
            dest.close()
        if check_type == 'panel-single':
            tgt_type = 'list'
        else:
            tgt_type = 'nodegroup'
            sgroup = SaltGroup.objects.get(pk=tgt_select)
            tgt_select = sgroup.groupname

        src_dir = '/opt/SOMS-master/soms/media/salt/fileupload/user_%s' % (request.user.id)
        dst_path = '/srv/backup/user_%s/%s/%s' % (request.user.id, tag, remote_path)
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])
        jid = sapi.remote_module(tgt_select, 'state.sls', 'file_upload',
                                 {'SALTSRC': src_dir, 'dst_path': dst_path, 'src_path': tag, 'remote_path': remote_path,
                                  'files': [f.name for f in files_upload]}, tgt_type)
        rst_source = sapi.salt_runner(jid)
        rst = rst_source['info'][0]['Result']

        return JsonResponse(rst)


@login_required
def salt_ajax_shell_file_upload(request):
    '''
    执行shell脚本文件上传
    '''
    if request.is_ajax():
        check_type = request.POST.get('check_type')
        tgt_select = SaltHost.objects.filter(status=True)
        hoh = ''
        for i in tgt_select:
            hoh += i.hostname
            hoh += ','
        tgt_select = hoh[:-1]
        files_upload = request.FILES.getlist('files_upload', None)
        remote_path = request.POST.get('remote_path', 'home/').strip(' ')
        remark = request.POST.get('remark', None)
        tag = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        upload_dir = '/opt/SOMS-master/soms/media/salt/fileupload/user_%s/%s' % (request.user.id, tag)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        for file in files_upload:
            dest = open(os.path.join(upload_dir, file.name), 'wb+')
            for chunk in file.chunks():
                dest.write(chunk)
            dest.close()
        if check_type == 'panel-single':
            tgt_type = 'list'
        else:
            tgt_type = 'nodegroup'
            sgroup = SaltGroup.objects.get(pk=tgt_select)
            tgt_select = sgroup.groupname
        src_dir = '/opt/SOMS-master/soms/media/salt/fileupload/user_%s' % (request.user.id) + '/' + tag
        dst_path = '/srv/backup/user_%s/%s/%s' % (request.user.id, tag, remote_path)
        sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                       password=settings.SALT_API['password'])

        print '本地路径：' + src_dir
        print '服务器路径：' + dst_path
        print 'tag' + tag
        print 'remote_path' + remote_path
        print [f.name for f in files_upload]
        jid = sapi.remote_module(tgt_select, 'state.sls', 'file_upload',
                                 {'SALTSRC': src_dir, 'dst_path': dst_path, 'src_path': tag, 'remote_path': remote_path,
                                  # 'files': [f.name for f in files_upload]}, tgt_type)
                                  'files': [f.name for f in files_upload]}, tgt_type)
        rst_source = sapi.salt_runner(jid)
        rst = rst_source['info'][0]['Result']
        is_exist = FilesUpload.objects.filter(files_name=file.name)
        if is_exist:
            FilesUpload.objects.filter(files_name=file.name).update(
                files_path=dst_path)
        else:
            FilesUpload.objects.create(
                files_name=file.name,files_path=dst_path)
        
        
        return JsonResponse(rst)


@login_required
def salt_file_rollback(request):
    '''
    文件回滚界面
    '''
    if request.user.has_perm('deploy.view_filemanage'):
        form = SaltFileForm()
        return render(request, 'salt_file_rollback.html', {'form': form, 'groups': ['panel-single', 'panel-group']})
    else:
        raise Http404


@login_required
def salt_ajax_file_rollback(request):
    '''
    执行文件回滚
    '''
    if request.user.has_perms(['deploy.view_filemanage', 'deploy.edit_fileupload']):
        true = True
        if request.method == 'POST':
            if request.is_ajax():
                r_list = []
                if request.POST.get('check_type') == 'rollback_file':
                    if request.POST.get('get_type') == 'panel-group':
                        grp = request.POST.get('tgt_select')
                        tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                    else:
                        tgt_select = request.POST.get('tgt_select')
                    rollback_list = FileRollback.objects.filter(target=tgt_select)
                    r_list = []
                    for r in rollback_list:
                        r_list.append(r.cur_path)
                    func = lambda x, y: x if y in x else x + [y]
                    r_list = reduce(func, [[], ] + r_list)
                    return HttpResponse(json.dumps(r_list))

                if request.POST.get('check_type') == 'rollback_history_list':
                    if request.POST.get('get_type') == 'panel-group':
                        grp = request.POST.get('tgt_select')
                        tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                    else:
                        tgt_select = request.POST.get('tgt_select')
                    cur_path = request.POST.get('rollback_list', None)
                    rollback_history_list = FileRollback.objects.filter(cur_path=cur_path).filter(target=tgt_select)
                    for r in rollback_history_list:
                        r_list.append(r.file_tag)
                    return HttpResponse(json.dumps(r_list))

                if request.POST.get('check_type') == 'rollback_history_remark':
                    if request.POST.get('get_type') == 'panel-group':
                        grp = request.POST.get('tgt_select')
                        tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                    else:
                        tgt_select = request.POST.get('tgt_select')
                    cur_path = request.POST.get('rollback_list', None)
                    file_tag = request.POST.get('rollback_remark', None)
                    rollback_history_remark = FileRollback.objects.filter(cur_path=cur_path).filter(file_tag=file_tag) \
                        .filter(target=tgt_select)
                    for r in rollback_history_remark:
                        r_list.append(r.remark)

                    return HttpResponse(json.dumps(r_list))

                else:
                    if request.POST.get('check_type') == 'panel-group':
                        grp = request.POST.get('tgt_select')
                        tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                        tgt_type = 'nodegroup'
                    else:
                        tgt_select = request.POST.get('tgt_select')
                        tgt_type = 'list'
                    remote_path = request.POST.get('remote_path')
                    file_tag = request.POST.get('tag')
                    sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                                   password=settings.SALT_API['password'])
                    file_tag_new = '%s%s' % (request.user.id, datetime.datetime.now().strftime('%j%Y%m%d%H%M%S'))
                    # 回滚前备份远程文件
                    ret_bak = sapi.file_manage(tgt_select, 'file_bakup.Backup', remote_path, file_tag_new, None,
                                               tgt_type)
                    # 文件回滚
                    ret = sapi.file_manage(tgt_select, 'file_bakup.Rollback', remote_path, file_tag, None, tgt_type)
                    rst = ''
                    for k in ret:
                        rst = rst + u'主机：' + k + '\n回滚结果：\n' + ret[k] + '\n' + '-' * 80 + '\n'

                    Message.objects.create(type=u'文件管理', user=request.user.first_name, action=u'文件回滚',
                                           action_ip=UserIP(request), content=u'文件回滚 %s' % rst)

                    return HttpResponse(json.dumps(rst))
    else:
        raise Http404


@login_required
def salt_task_list(request):
    '''
    任务列表
    '''
    if request.user.has_perm('userperm.view_message'):
        if request.method == 'GET':
            if request.GET.has_key('tid'):
                tid = request.get_full_path().split('=')[1]
                log_detail = Message.objects.filter(user=request.user.first_name).filter(id=tid).exclude(
                    type=u'用户登录').exclude(type=u'用户退出')
                return render(request, 'salt_task_detail.html', {'log_detail': log_detail})

        logs = Message.objects.filter(user=request.user.first_name).exclude(type=u'用户登录').exclude(type=u'用户退出')[:200]

        return render(request, 'salt_task_list.html', {'all_logs': logs})
    else:
        raise Http404


@login_required
def salt_task_check(request):
    '''
    任务查询
    '''
    return render(request, 'salt_task_check.html', {})


@login_required
def salt_task_running(request):
    '''
    获取运行中的任务
    '''
    ret = []
    if request.method == 'POST':
        if request.user.has_perms(['userperm.view_message', 'deploy.edit_deploy']):
            if request.is_ajax():
                sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                               password=settings.SALT_API['password'])
                rst = sapi.salt_running_jobs()
                for k, v in rst.items():
                    dict = {}
                    dict['jid'] = k
                    dict['func'] = v['Function']
                    dict['tgt_type'] = v['Target-type']
                    dict['running'] = v['Arguments'][0].replace(';echo ":::"$?', '')
                    str_tgt = ''
                    for i in v['Running']:
                        for m, n in i.items():
                            str_tgt = str_tgt + m + ':' + str(n) + '<br />'
                    dict['tgt_pid'] = str_tgt
                    ret.append(dict)
                return HttpResponse(json.dumps(ret))
    if request.GET.has_key('delete'):
        jid = request.GET.get('jid')
        import subprocess
        p = subprocess.Popen("salt '*' saltutil.term_job %s" % jid, shell=True, stdout=subprocess.PIPE)
        out = p.stdout.readlines()
        return HttpResponse(json.dumps('Job %s killed.' % jid))

    return render(request, 'salt_task_running_list.html', {})


@login_required
def project_list(request):
    '''
    项目列表
    '''
    if request.user.has_perm('deploy.view_project'):
        if request.user.is_superuser:
            project_list = Project.objects.all()
        else:
            user_group = User.objects.get(pk=request.user.id).group.all()
            for g in user_group:
                project_list = Project.objects.filter(user_group=g)
        return render(request, 'salt_project_list.html', {'projects': project_list})
    else:
        raise Http404


@login_required
def project_manage(request, id=None):
    '''
    项目管理
    :param request:
    :param id:
    :return:
    '''
    rsync_conf = '/opt/SOMS-master/soms/media/salt/rsync'
    if request.user.has_perm('deploy.view_project'):
        content = ''
        if id:
            project = get_object_or_404(Project, pk=id)
            action = 'edit'
            page_name = '编辑项目'
            try:
                with open('%s/%s.list' % (rsync_conf, project.name), 'r') as f:
                    content = f.read()
            except:
                pass
        else:
            project = Project()
            action = 'add'
            page_name = '新增项目'

        if request.method == 'GET':
            if request.GET.has_key('delete'):
                id = request.GET.get('id')
                project = get_object_or_404(Project, pk=id)
                project.delete()
                Message.objects.create(type=u'部署管理', user=request.user.first_name, action=u'删除项目',
                                       action_ip=UserIP(request), content=u'删除项目 %s' % project.pname)
                return redirect('project_list')

        if request.method == 'POST':
            form = ProjectForm(request.user, request.POST, instance=project)
            if form.is_valid():
                if action == 'add':
                    project = form.save(commit=False)
                    project.user = request.user
                else:
                    form.save
                project.name = form.cleaned_data['src'].split('/')[-1].replace('.git', '')
                project.save()
                exclude = request.POST.get('exclude')
                try:
                    if not os.path.isdir(rsync_conf):
                        os.makedirs(rsync_conf)
                    with open('%s/%s.list' % (rsync_conf, project.name), 'w') as f:
                        f.write(exclude)
                except:
                    pass
                Message.objects.create(type=u'部署管理', user=request.user.first_name, action=page_name,
                                       action_ip=UserIP(request), content='%s %s' % (page_name, project.pname))

                return redirect('project_list')
        else:
            form = ProjectForm(request.user, instance=project)

        return render(request, 'salt_project_manage.html',
                      {'form': form, 'action': action, 'page_name': page_name, 'aid': id, 'content': content})
    else:
        raise Http404


@login_required
def project_deploy(request):
    '''
    项目部署
    :param request:
    :return:
    '''
    if request.user.has_perm('deploy.edit_project'):
        if request.method == 'GET':
            if request.is_ajax():
                id = request.GET.get('id')
                env = request.GET.get('env')
                project = Project.objects.get(pk=id)
                if env == '0':
                    tgt_list = project.salt_test
                elif env == '1':
                    tgt_list = project.salt_group
                else:
                    pass
                if tgt_list == '0':
                    ret = {u'发布异常': {'result': u'请确认是否配置测试/正式环境'}}
                    if request.GET.has_key('get_rollback'):
                        ret = {'-1': u'请确认是否配置测试/正式环境'}
                    return HttpResponse(json.dumps(ret))
                tgt_type = 'nodegroup'
                action = ''
                url = project.src.split('//')
                sapi = SaltAPI(url=settings.SALT_API['url'], username=settings.SALT_API['user'],
                               password=settings.SALT_API['password'])
                dtime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                ret = sapi.file_copy(tgt_list, 'cp.get_file', 'salt://rsync/%s.list' % project.name,
                                     '/srv/salt/%s.list' % project.name, 'nodegroup')
                if request.GET.has_key('init'):
                    action = u'初始化项目'
                    ret = sapi.project_manage(tgt_list, 'project_manage.ProjectSync', project.name,
                                              '%s//%s:%s@%s' % (url[0], project.src_user, project.src_passwd, url[1]),
                                              project.path, 'init', dtime, tgt_type)

                if request.GET.has_key('update'):
                    action = u'更新项目'
                    try:
                        ret = sapi.project_manage(tgt_list, 'project_manage.ProjectSync', project.name,
                                                  '%s//%s:%s@%s' % (
                                                  url[0], project.src_user, project.src_passwd, url[1]),
                                                  project.path, 'update', dtime, tgt_type)
                        for _, v in ret.items():
                            if v['tag']:
                                ProjectRollback.objects.create(name=project, tag=v['tag'], env=env)
                                break
                    except:
                        ret = {u'更新异常': {'result': u'更新失败，检查项目是否发布'}}

                if request.GET.has_key('get_rollback'):
                    action = u'获取备份'
                    ret = {i['pk']: i['tag'] for i in
                           ProjectRollback.objects.filter(name=id).filter(env=env).values('pk', 'tag')}
                    if not ret:
                        ret = {'0': 'No backup found.'}

                if request.GET.has_key('rollback_delete'):
                    action = u'删除备份'
                    tag = request.GET.get('tag')
                    enforce = request.GET.get('enforce')
                    ret = sapi.project_manage(tgt_list, 'project_manage.ProjectClean', project.name, tag,
                                              project.path, 'delete', dtime, tgt_type)
                    for _, v in ret.items():
                        if v['tag'] or enforce == '1':
                            ProjectRollback.objects.get(name=project, tag=tag, env=env).delete()
                            break

                if request.GET.has_key('rollback'):
                    action = u'回滚项目'
                    tag = request.GET.get('tag')
                    ret = sapi.project_manage(tgt_list, 'project_manage.ProjectRollback', project.name, tag,
                                              project.path, 'rollback', dtime, tgt_type)

                if request.GET.has_key('start'):
                    action = u'启动进程'
                    tag = request.GET.get('tag')
                    if tag:
                        ret = ProjectExec(sapi, tgt_list, 'cmd.run', tag, tgt_type)
                    else:
                        ret = {u'进程管理': {'result': u'未配置启动项'}}

                if request.GET.has_key('reload'):
                    action = u'重启进程'
                    tag = request.GET.get('tag')
                    if tag:
                        ret = ProjectExec(sapi, tgt_list, 'cmd.run', tag, tgt_type)
                    else:
                        ret = {u'进程管理': {'result': u'未配置重启项'}}

                if request.GET.has_key('stop'):
                    action = u'停止进程'
                    tag = request.GET.get('tag')
                    if tag:
                        ret = ProjectExec(sapi, tgt_list, 'cmd.run', tag, tgt_type)
                    else:
                        ret = {u'进程管理': {'result': u'未配置停止项'}}

                Message.objects.create(type=u'项目管理', user=request.user.first_name, action=action,
                                       action_ip=UserIP(request), content='%s %s' % (project.pname, ret))

                return HttpResponse(json.dumps(ret))

        return redirect(project_list)
    else:
        raise Http404


@login_required
def ajax_user_groups(request):
    user_groups = {i['pk']: i['group_name'] for i in
                   User.objects.get(pk=request.user.pk).group.values('pk', 'group_name')}

    return JsonResponse(user_groups)
