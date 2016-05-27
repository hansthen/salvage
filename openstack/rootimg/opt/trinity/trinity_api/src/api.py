import os
import shutil
from ConfigParser import SafeConfigParser
from bottle import Bottle,get,put,post,delete,run,request,response,abort
import json
import requests
from collections import defaultdict
import re
import subprocess
import base64
import time
import tzlocal

conf_file='/etc/trinity/trinity_api.conf'
config=SafeConfigParser()
config.read(conf_file)
trinity_host=config.get('trinity','trinity_host')
trinity_port=config.getint('trinity','trinity_port')
trinity_debug=config.getboolean('trinity','trinity_debug')
trinity_server=config.get('trinity','trinity_server')
xcat_host=config.get('xcat','xcat_host')
trinity_user=config.get('xcat','trinity_user')
trinity_password=config.get('xcat','trinity_password')
node_pref=config.get('cluster','node_pref')
cont_pref=config.get('cluster','cont_pref')

xcat_version = subprocess.check_output('/opt/xcat/bin/lsxcatd -v', shell=True)
version = re.search(r'Version \d+\.(\d+)(\.\d+)?\s', xcat_version)
if version and int(version.group(1)) < 10:
    password_parm = 'password'
else:
    password_parm = 'userPW'

# Globals here
# state_has_changed = False
# cached_detailed_overview = {}

class TrinityAPI(object):
  def __init__(self,request):
    self.request=request
    self.has_authenticated=False
    self.config(conf_file)
    self.tenant=self.request.get_header('X-Tenant',default=None)
    self.token=self.request.get_header('X-Auth-Token',default=None)
    self.set_attrs_from_json()
    # This is a hack to allow for username/password based authentication for get requests during testing
    if (not (self.token or hasattr(self,'password'))) and self.request.auth:
      (self.username,self.password)=self.request.auth
    self.errors()
    self.query = {'userName': self.trinity_user, password_parm: self.trinity_password }
    self.headers={"Content-Type":"application/json", "Accept":"application/json"} # setting this by hand for now
    self.authenticate()    

  def config(self,file):
    config=SafeConfigParser()
    config.read(file)
    for section in config.sections():
      for option in config.options(section):
        value=config.get(section,option)
        setattr(self,option,value)

  # Get value for a given key from the JSON body of request  
  def set_attrs_from_json(self):
    body_dict=self.request.json
    if body_dict:
      for key in body_dict:
        setattr(self,key,body_dict[key])

  def errors(self):
    self.no_access='Access denied!'
    self.not_admin='Only admin has permission!'
    self.no_nodes='Not enough resources!'
    self.xcat_error='xCAT error'

  
  # Authenticate against Keystone. 
  def authenticate(self):
    if self.has_authenticated: 
      return
    if self.token:
      payload = { 
                  "auth": {
                    "tenantName": self.tenant,
                    "token": {
                      "id": self.token
                    }
                  }
                }
    else:
      payload = { 
                  "auth": {
                    "tenantName": self.tenant,
                    "passwordCredentials": {
                      "username": self.username,
                      "password": self.password
                    }
                  }
                }
  
    r = requests.post(self.keystone_host+'/tokens', data=json.dumps(payload), headers=self.headers)
    self.tenant_id=r.json()["access"]["token"]["tenant"]["id"]
    self.has_access = (r.status_code  == requests.codes.ok )
    self.is_admin=False
    if self.has_access: 
      self.has_authenticated=True
      body = r.json()
      # self.is_admin = body["access"]["metadata"]["is_admin"]
      # This is a hack to get around a bug in Keystone
      self.is_admin = (body['access']['user']['name'] == 'admin')
      self.token = body["access"]["token"]["id"]

  # xCAT API request
  def xcat(self,verb='GET',path='/',payload={}):
    methods={'GET': requests.get, 'POST': requests.post, 'PUT': requests.put, 'DELETE': requests.delete}
    r=methods[verb](self.xcat_host+path,verify=False,params=self.query,headers=self.headers,data=json.dumps(payload))
    try:
      return r.json()  
    except:
      return {}
####################################################
   
  def groups(self,name='groups',startkey=''):
    self.authenticate()
    status_ok=False
    groups=[]
    if self.has_access: # and self.is_admin:
      xcat_groups=self.xcat('GET','/groups')
      l=len(startkey)
      for group in xcat_groups:
        if group.startswith(startkey):
          groups.append(group[l:])  
      status_ok=True
    return {'statusOK':status_ok, name:groups}
   
  def detailed_overview(self):
    global state_has_changed
    global all_nodes_info
    global cached_detailed_overview
    if not state_has_changed:
      return cached_detailed_overview
 
    xcat_groups=self.xcat('GET','/groups')
    hc_list=[]
    for group in xcat_groups:
      if group.startswith(self.hw): hc_list.append(group)
      if group.startswith(self.vc): hc_list.append(group)
    hc_string=",".join(hc_list)
    xcat_overview=self.xcat('GET','/groups/'+hc_string+'/attrs/members')
    hc_overview={'hardware':{},'cluster':{}}
    lhw=len(self.hw)
    lvc=len(self.vc)
    for hc in xcat_overview:
      if hc.startswith(self.hw): 
        hardware=hc[lhw:]
        members=xcat_overview[hc]['members'].strip()
        node_list=[]
        if members: node_list=[x.strip() for x in members.split(',')]
        hc_overview['hardware'][hardware]=node_list
      if hc.startswith(self.vc): 
        cluster=hc[lvc:]
        members=xcat_overview[hc]['members'].strip()
        node_list=[]
        if members: node_list=[x.strip() for x in members.split(',')]
        hc_overview['cluster'][cluster]=node_list
    self.overview=hc_overview
    cached_detailed_overview=hc_overview
    state_has_changed=False
    return hc_overview

 
  def nodes(self):
    self.authenticate()
    status_ok=False
    nodes=[]
    if self.has_access and self.is_admin:
      nodes=self.xcat('GET','/nodes')
      status_ok=True
    return {'statusOK':status_ok,'nodes':nodes}
  
  def node_info(self,node):
    self.authenticate()
    status_ok=False
    if self.has_access :
      xcat_node=self.xcat('GET','/nodes/'+node)
      info={'hardware': None, 'cluster': None}
      lhw=len(self.hw)
      lvc=len(self.vc)
      members=xcat_node[node]['groups'].strip()
      groups=[]
      if members: groups=[x.strip() for x in members.split(',')]
      for group in groups:
        # Assumes that the node is only a part of one hw and one vc 
        if group.startswith(self.hw): 
          info['hardware']=group[lhw:] 
        if group.startswith(self.vc): 
          info['cluster']=group[lvc:]
      status_ok=True
      info['statusOK']=status_ok
    return info
   
  def nodes_info(self, node_list):
    node_string=",".join(node_list)
    xcat_nodes=self.xcat('GET','/nodes/'+node_string)
    lhw=len(self.hw)
    lvc=len(self.vc)
    info_dict={}
    for node,info in xcat_nodes.items():
      info_dict[node]={'hardware':None,'cluster':None}
      members=info['groups'].strip()
      groups=[]
      if members: groups=[x.strip() for x in members.split(',')]
      for group in groups:
        # Assumes that the node is only a part of one hw and one vc 
        if group.startswith(self.hw): 
          info_dict[node]['hardware']=group[lhw:] 
        if group.startswith(self.vc): 
          info_dict[node]['cluster']=group[lvc:]
    return info_dict
     
  def group_nodes(self,name,startkey=''):
    self.authenticate()
    status_ok=False
    nodes=[]
    group_name=startkey+name
    if self.has_access:
      xcat_nodes=self.xcat('GET','/groups/'+group_name+'/attrs/members')
      members=xcat_nodes[group_name]['members'].strip()
      nodes=[]
      # Hack because of unicode
      if members: nodes=[x.strip() for x in members.split(',')]
      status_ok=True
    return  {'statusOK':status_ok, 'nodes' : nodes}
  
  def cluster_nodes(self,cluster):
    self.authenticate()
    ret={}
    ret['statusOK']=True
    if not (self.is_admin or self.tenant==cluster):
      return ret
    ret['hardware']=  {} 
    hc_overview=self.detailed_overview()
    all_nodes=set(hc_overview['cluster'][cluster])
    for hardware in hc_overview['hardware']:
      overlap=len(all_nodes.intersection(set(hc_overview['hardware'][hardware])))
      ret['hardware'][hardware]=overlap
    return ret    

  # this is not DRY
  def cluster_details(self,cluster): 
    self.authenticate()
    ret={}
    ret['statusOK']=True
    if not (self.is_admin or self.tenant==cluster):
      return ret
    ret['hardware']={}
    hc_overview=self.detailed_overview()
    all_nodes=set(hc_overview['cluster'][cluster])
    for hardware in hc_overview['hardware']:
      overlap=list(all_nodes.intersection(set(hc_overview['hardware'][hardware])))
      ret['hardware'][hardware]=overlap
 
    return ret    

  def hardware_nodes(self,hardware):
    self.authenticate()
    ret={}
    ret['statusOK']=True
    if not (self.is_admin):
      return ret
    hc_overview=self.detailed_overview()
    c_nodes=set()
    for cluster in hc_overview['cluster']:
      c_nodes=c_nodes.union(set(hc_overview['cluster'][cluster]))
    ret['total']=len(hc_overview['hardware'][hardware])
    ret['list_unallocated']=list(set(hc_overview['hardware'][hardware])-c_nodes)
    ret['unallocated']=len(ret['list_unallocated'])  
    ret['allocated']=ret['total']-ret['unallocated']   

    return ret    

  def cluster_change_nodes(self,cluster,old_list,hw_dict):
    self.authenticate()
    ret={}
    ret['statusOK']=False
    xcat_cluster=self.vc+cluster
    if not(self.has_access and self.is_admin):
      return ret 
    node_list=old_list[:]
    subs_list=[]
    adds_list=[]
    for hardware in hw_dict:
      if hardware not in self.specs:
        for node in hw_dict[hardware]:
          node_list.remove(node)
          subs_list.append(node)
    for hardware in self.specs:
      d_nodes=self.specs[hardware]
      if hardware in hw_dict:
        e_nodes=hw_dict[hardware]
        if len(e_nodes) == d_nodes: 
          continue
        elif len(e_nodes) > d_nodes:
          sub_num=len(e_nodes)-d_nodes
          subs=e_nodes[-sub_num:]
          for node in subs:
            node_list.remove(node)
            subs_list.append(node)
        else:
          add_num=d_nodes-len(e_nodes)
          h_nodes=self.hardware_nodes(hardware)
          if add_num > h_nodes['unallocated']:
            ret['error']=self.no_nodes
            return ret
          else:
            for node in h_nodes['list_unallocated'][:add_num]:
              node_list.append(node)
              adds_list.append(node)
      else:
        h_nodes=self.hardware_nodes(hardware)
        # Not DRY
        if d_nodes > h_nodes['unallocated']:
          ret['error']=self.no_nodes
          return ret
        else:
          for node in h_nodes['list_unallocated'][:d_nodes]:
            node_list.append(node)
            adds_list.append(node)
    if adds_list or subs_list:
      ret['change']=True
      if node_list:
        node_string=",".join(node_list)
        payload={'members': node_string}
        r=self.xcat(verb='PUT',path='/groups/'+xcat_cluster,payload=payload)
      else:
        # workaround for empty nodelist (deleting cluster)
        # Note: the group definition will still survive
        node_string=old_list[0]
        last_node=old_list[0]
        payload={'members': node_string}
        r=self.xcat(verb='PUT',path='/groups/'+xcat_cluster,payload=payload)
        r=self.xcat(verb='GET',path='/nodes/'+last_node+'/attrs/groups')
        node_groups=r[last_node]["groups"]
        node_groups_list=node_groups.strip().split(",")
        node_groups_list.remove(xcat_cluster)
        node_groups=",".join(node_groups_list)
        payload={"groups":node_groups}
        r=self.xcat(verb='PUT',path='/nodes/'+last_node,payload=payload)
        
      if hasattr(r,'status_code'):   
        if r.status_code == requests.codes.ok:
          ret['statusOK']=True
        else:
          ret['statusOK']=False
          ret['error']=self.xcat_error
      else:
        ret['statusOK']=True
    else:
      ret['statusOK']=True
      ret['change']=False
    ret['nodeList']= node_list 
    ret['subsList']=subs_list
    ret['addsList']=adds_list 
    return ret


  def mon_info(self):
    self.authenticate()
    ret={}
    if self.has_access and self.is_admin:
      ret.update({'monUser':self.mon_user})      
      ret.update({'monPass':self.mon_pass})      
      ret.update({'monHost':self.mon_host})  
      ret.update({'monRoot':self.mon_root})    
    return ret
