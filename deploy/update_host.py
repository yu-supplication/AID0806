#!/usr/bin/env python
#-*- coding:UTF-8 -*-
import sys
sys.path.insert(0, '../')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'soms.settings' # 指定使用的配置文件
import django
django.setup()



import time
import traceback
import commands
from deploy.models import UpdateHostInfo, SaltHost
from soms import settings
from deploy.saltapi import SaltAPI

DISKINFO=commands.getoutput("lsblk -b |grep -B 1 part |grep -w disk |sed '/fd0/d' |awk '{print $4}' |awk '{sum+=$1} END {print sum/1024/1024/1024}'").split()


def GetInfoDict(r, arg):
    try:
        result = ''
        for k in r[arg]:
            result = result + k + ': ' + str(r[arg][k]) + '\n'
    except:
        result = 'Nan'
    return result

def GetInfo(r, arg):
    try:
        arg = str(r[arg])
    except:
        arg = 'Nan'
    return arg


def GetAssetInfo(tgt):
    '''
    Salt API获取主机信息并进行格式化输出
    '''
    info = {}
    sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
    ret = sapi.remote_server_info(tgt, 'grains.items')
    info['sn']=GetInfo(ret,'serialnumber')
    info['hostname']=GetInfo(ret,'fqdn')
    info['nodename']=tgt
    info['os']=GetInfo(ret,'os')+GetInfo(ret,'osrelease')+' '+GetInfo(ret,'osarch')
    info['manufacturer']=GetInfo(ret,'manufacturer')
    info['cpu_model']=GetInfo(ret,'cpu_model')
    info['productname']=GetInfo(ret,'productname')
    info['cpu_nums']=GetInfo(ret,'num_cpus')
    info['disk'] = str(DISKINFO[0])+"GB"
    info['network'] = GetInfo(ret,'PublicIp')
    info['kernel'] = GetInfo(ret,'kernel') + GetInfo(ret,'kernelrelease')
    info['zmqversion'] = GetInfo(ret,'zmqversion')
    info['shell'] = GetInfo(ret,'shell')
    info['saltversion'] = GetInfo(ret,'saltversion')
    info['locale'] = GetInfoDict(ret, 'locale_info')
    info['selinux'] = GetInfoDict(ret, 'selinux')
    info['networkarea'] = GetInfo(ret, 'netRegion')

    if 'virtual_subtype' in ret:
        virtual = GetInfo(ret,'virtual') + '-' + GetInfo(ret,'virtual_subtype')
    else:
        virtual=GetInfo(ret,'virtual')
    info['virtual'] = virtual

    mem=GetInfo(ret,'mem_total')
    if mem > 1000:
        mem = int(mem)/1000.0
        memory = ('%.1f'%mem) + 'G'
    else:
        memory = str(mem) + 'M'
    info['memory'] = memory

    return info

def save_info(info):
	sn_by_info = UpdateHostInfo.objects.filter(sn=info['sn'])
	if sn_by_info:
		UpdateHostInfo.objects.filter(sn=info['sn']).update(
								sn=info['sn'],
							    hostname=info['hostname'],
							    nodename=info['nodename'],
							    os=info['os'],
							    manufacturer=info['manufacturer'],
							    cpu_model=info['cpu_model'],
							    productname=info['productname'],
							    cpu_nums=info['cpu_nums'],
							    disk=info['disk'],
							    network=info['network'],
							    kernel=info['kernel'],
							    zmqversion=info['zmqversion'],
							    shell=info['shell'],
							    saltversion=info['saltversion'],
							    locale=info['locale'],
							    selinux=info['selinux'],
							    networkarea=info['networkarea'],
							    virtual=info['virtual'],
							    memory=info['memory'],
			)
	else:
		UpdateHostInfo.objects.create(	
								sn=info['sn'],
							    hostname=info['hostname'],
							    nodename=info['nodename'],
							    os=info['os'],
							    manufacturer=info['manufacturer'],
							    cpu_model=info['cpu_model'],
							    productname=info['productname'],
							    cpu_nums=info['cpu_nums'],
							    disk=info['disk'],
							    network=info['network'],
							    kernel=info['kernel'],
							    zmqversion=info['zmqversion'],
							    shell=info['shell'],
							    saltversion=info['saltversion'],
							    locale=info['locale'],
							    selinux=info['selinux'],
							    networkarea=info['networkarea'],
							    virtual=info['virtual'],
							    memory=info['memory'],
			)

def main():
	while True:
	    # 获取信息
	    try:
	        q = SaltHost.objects.filter(alive=True)
	        

	        tgt_list = [i.hostname for i in q]
	        for i in tgt_list:
	        	info = GetAssetInfo(i)
	        	save_info(info)
	        	# time.sleep(1)

	    except Exception as e:
	    	print traceback.format_exc()
	        continue
	    time.sleep(1)

if __name__ == '__main__':
    main()