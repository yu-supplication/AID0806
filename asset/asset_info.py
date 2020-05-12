#!/usr/bin/env python
# coding: utf8
'''
@author: qitan
@contact: qqing_lai@hotmail.com
@file: asset_info.py
@time: 2017/3/30 15:33
@desc:
'''

from deploy.saltapi import SaltAPI
from soms import settings
import threading
import commands
import time

import multiprocessing

asset_info = []

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

DISKINFO=commands.getoutput("lsblk -b |grep -B 1 part |grep -w disk |sed '/fd0/d' |awk '{print $4}' |awk '{sum+=$1} END {print sum/1024/1024/1024}'").split()

def GetAssetInfo(tgt):
    '''
    Salt API获取主机信息并进行格式化输出
    '''
    global asset_info
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

#    try:
#        hwaddr = ret['hwaddr_interfaces']
#        ipaddr = ret['ip4_interfaces']
#        hwaddr.pop('lo')
#        ipaddr.pop('lo')
#        network = ''
#        for i in ipaddr:
#            ip = ''
#            for j in ipaddr[i]:
#                ip = ip + j + '/'
#            network = network + i + ': ' + ip.strip('/') + '-' + hwaddr[i] + '\n'
#        info['network'] =  network
#    except:
#        info['network'] = 'Nan'
#
    mem=GetInfo(ret,'mem_total')
    if mem > 1000:
        mem = int(mem)/1000.0
        memory = ('%.1f'%mem) + 'G'
    else:
        memory = str(mem) + 'M'
    info['memory'] = memory

#    ret = sapi.remote_server_info(tgt, 'disk.usage')
#    disk = ''
#    for i in ret:
#        r = int(ret[i]['1K-blocks'])/1000
#        if r > 1000:
#            r = r/1000
#            s = str(r) + 'G'
#            if r > 1000:
#                r = r/1000.0
#                s = ('%.1f'%r) + 'T'
#        else:
#            s = str(r) + 'M'
#        disk = disk + i + ': ' + s + '\n'
#    info['disk'] = disk

    asset_info.append(info)

def MultipleCollect(tgt_list):
    global asset_info
    asset_info = []
    threads = []
    loop = 0
    count = len(tgt_list)
    for i in range(0, count, 2):
        keys = range(loop*2, (loop+1)*2, 1)

        #实例化线程
        for i in keys:
            if i >= count:
                break
            else:
                t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
                threads.append(t)
        #启动线程
        for i in keys:
            if i >=count:
                break
            else:
                threads[i].start()
        #等待并发线程结束
        for i in keys:
            if i >= count:
                break
            else:
                threads[i].join()
        loop = loop + 1
    # print(asset_info)
    return asset_info


# def MultipleCollect(tgt_list):
#     global asset_info
#     asset_info = []
#     tgt_list1 = []
#     tgt_list2 = []
#     tgt_list3 = []
#     tgt_list4 = []
#     tgt_list5 = []
#     for x in xrange(1,200):
#         tgt_list1.append(tgt_list[0])
#     for x in xrange(1,200):
#         tgt_list2.append(tgt_list[0])
#     for x in xrange(1,200):
#         tgt_list3.append(tgt_list[0])
#     for x in xrange(1,200):
#         tgt_list4.append(tgt_list[0])
#     for x in xrange(1,200):
#         tgt_list5.append(tgt_list[0])
#     start_time=time.time()  #开始时间    
#     print 'qqqqqqqqqqqqqqqq',tgt_list1
#     p1 = multiprocessing.Process(target = MultipleCollect1, args = (tgt_list1,))
#     p1.start()
#     p2 = multiprocessing.Process(target = MultipleCollect2, args = (tgt_list2,))
#     p2.start()
#     p3 = multiprocessing.Process(target = MultipleCollect3, args = (tgt_list3,))
#     p3.start()
#     p4 = multiprocessing.Process(target = MultipleCollect4, args = (tgt_list4,))
#     p4.start()
#     p5 = multiprocessing.Process(target = MultipleCollect5, args = (tgt_list5,))
#     p5.start()
#     end_time=time.time()   #结束时间
#     print("time:%d"  % (end_time-start_time))  #结束时间-开始时间
#     return asset_info

# def MultipleCollect1(tgt_list):
#     # global asset_info
#     # asset_info = []
#     threads = []
#     loop = 0
#     count = len(tgt_list)
#     for i in range(0, count, 6):
#         keys = range(loop*6, (loop+1)*6, 1)

#         #实例化线程
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
#                 threads.append(t)
#         #启动线程
#         for i in keys:
#             if i >=count:
#                 break
#             else:
#                 threads[i].start()
#         #等待并发线程结束
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 threads[i].join()
#         loop = loop + 1
#     # print(asset_info)
#     # return asset_info

# def MultipleCollect2(tgt_list):
#     # global asset_info
#     # asset_info = []
#     threads = []
#     loop = 0
#     count = len(tgt_list)
#     for i in range(0, count, 6):
#         keys = range(loop*6, (loop+1)*6, 1)

#         #实例化线程
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
#                 threads.append(t)
#         #启动线程
#         for i in keys:
#             if i >=count:
#                 break
#             else:
#                 threads[i].start()
#         #等待并发线程结束
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 threads[i].join()
#         loop = loop + 1

# def MultipleCollect3(tgt_list):
#     # global asset_info
#     # asset_info = []
#     threads = []
#     loop = 0
#     count = len(tgt_list)
#     for i in range(0, count, 6):
#         keys = range(loop*6, (loop+1)*6, 1)

#         #实例化线程
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
#                 threads.append(t)
#         #启动线程
#         for i in keys:
#             if i >=count:
#                 break
#             else:
#                 threads[i].start()
#         #等待并发线程结束
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 threads[i].join()
#         loop = loop + 1
# def MultipleCollect4(tgt_list):
#     # global asset_info
#     # asset_info = []
#     threads = []
#     loop = 0
#     count = len(tgt_list)
#     for i in range(0, count, 6):
#         keys = range(loop*6, (loop+1)*6, 1)

#         #实例化线程
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
#                 threads.append(t)
#         #启动线程
#         for i in keys:
#             if i >=count:
#                 break
#             else:
#                 threads[i].start()
#         #等待并发线程结束
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 threads[i].join()
#         loop = loop + 1
# def MultipleCollect5(tgt_list):
#     # global asset_info
#     # asset_info = []
#     threads = []
#     loop = 0
#     count = len(tgt_list)
#     for i in range(0, count, 6):
#         keys = range(loop*6, (loop+1)*6, 1)

#         #实例化线程
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 t = threading.Thread(target=GetAssetInfo, args=(tgt_list[i],))
#                 threads.append(t)
#         #启动线程
#         for i in keys:
#             if i >=count:
#                 break
#             else:
#                 threads[i].start()
#         #等待并发线程结束
#         for i in keys:
#             if i >= count:
#                 break
#             else:
#                 threads[i].join()
#         loop = loop + 1