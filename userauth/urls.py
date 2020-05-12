from django.conf.urls import url
from django.contrib.auth import views as djviews
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^help/$', views.soms_help, name='help'),
    url(r'^about/$', views.soms_about, name='about'),
    url(r'^accounts/login/$', views.login, name='login'),
    url(r'^accounts/logout/$', views.logout, {'next_page': '/'}, name='logout'),
    #url(r'^accounts/login/$', djviews.login, name='login'),
    #url(r'^accounts/logout/$', djviews.logout, {'next_page': '/'}, name='logout'),
    url(r'^userauth/user/list/$', views.user_list, name='user_list'),
    url(r'^userauth/user/add/$', views.user_manage, name='user_add'),
    url(r'^userauth/user/edit/(?P<aid>\d+)/(?P<action>[\w-]+)/$', views.user_manage, name='user_manage'),
    url(r'^userauth/group/list/$', views.group_list, name='user_group_list'),
    url(r'^userauth/group/add/$', views.group_manage, name='user_group_add'),
    url(r'^userauth/group/edit/(?P<aid>\d+)/(?P<action>[\w-]+)/$', views.group_manage, name='user_group_manage'),
]
