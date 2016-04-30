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
      

    

######################################################################### 
trinity = Bottle()

@trinity.get('/trinity/v<version:float>/')
def welcome(version=1):
  return "Welcome to the Trinity API"

@trinity.get('/trinity/v<version:float>/version')
def version(version=1):
  fop=open('/trinity/version','r')
  lines=fop.readlines()
  fop.close()
  branch=lines[0].strip().split()[1]
  id=lines[1].strip().split()[0]
  id_branch = id + ' ('+branch+')'
  return {'versionID (releaseBranch)':id_branch }

@trinity.post('/trinity/v<version:float>/login')
def login(version=1):
  req=TrinityAPI(request)
  if req.has_access:
    response.status=200
    return {'token': req.token}
  else:
    response.status=401
    return

@trinity.get('/trinity/v<version:float>/overview')
def total_overview(version=1):
  req=TrinityAPI(request)
  if not req.is_admin:
    ret={'error':req.not_admin}
    return ret
  return req.detailed_overview()
 

@trinity.get('/trinity/v<version:float>/overview/hardwares')
def hardware_overview(version=1):
  req=TrinityAPI(request)
  if not req.is_admin:
    ret={'error':req.not_admin}
    return ret
  hc_overview=req.detailed_overview()
  c_nodes=set()
  for cluster in hc_overview['cluster']:
    c_nodes=c_nodes.union(set(hc_overview['cluster'][cluster]))
  
  h_overview={}
  for hardware in hc_overview['hardware']: 
    h_overview[hardware]={} 
    h_overview[hardware]['total']=len(hc_overview['hardware'][hardware])
    h_overview[hardware]['list_unallocated']=list(set(hc_overview['hardware'][hardware])-c_nodes)
    h_overview[hardware]['unallocated']=len(h_overview[hardware]['list_unallocated'])  
    h_overview[hardware]['allocated']=h_overview[hardware]['total']-h_overview[hardware]['unallocated']   
  return h_overview    
  
@trinity.get('/trinity/v<version:float>/overview/clusters')
def cluster_overview(version=1):
  req=TrinityAPI(request)
  if not req.is_admin:
    ret={'error':req.not_admin}
    return ret
  hc_overview=req.detailed_overview()
  c_overview={}
  for cluster in hc_overview['cluster']:
    c_overview[cluster]={}
    c_overview[cluster]['hardware']={}
    for hardware in hc_overview['hardware']:
      amount=len(set(hc_overview['cluster'][cluster]).intersection(set(hc_overview['hardware'][hardware])))
      c_overview[cluster]['hardware'][hardware]=amount
  return c_overview   



@trinity.get('/trinity/v<version:float>/clusters')
def list_clusters(version=1):
  req=TrinityAPI(request)
  clusters=req.detailed_overview()['cluster'].keys()
  return {'statusOK': True, 'clusters': clusters}

@trinity.get('/trinity/v<version:float>/hardwares')
def list_hardwares(version=1):
  req=TrinityAPI(request)
  hardwares=req.detailed_overview()['hardware'].keys()
  return {'statusOK': True, 'hardwares': hardwares}

@trinity.get('/trinity/v<version:float>/nodes')
def list_nodes(version=1):
  req=TrinityAPI(request)
  return req.nodes()

@trinity.get('/trinity/v<version:float>/nodes/<node>')
def show_node(node,version=1):
  req=TrinityAPI(request)
  # We do an authentication here because the object method is 
  # need by non-admin calls too
  req.authenticate()
  if req.is_admin:
    return req.node_info(node)
  else:
    return {'error':req.not_admin}

@trinity.get('/trinity/v<version:float>/clusters/<cluster>')
def show_cluster(cluster,version=1):
  req=TrinityAPI(request)
  if not (req.is_admin or req.tenant==cluster):
    ret={'error':req.no_access}
    return ret
  hc_overview=req.detailed_overview()
  c_overview={'hardware':{}}
  for hardware in hc_overview['hardware']:
    amount=len(set(hc_overview['cluster'][cluster]).intersection(set(hc_overview['hardware'][hardware])))
    c_overview['hardware'][hardware]=amount
  return c_overview   

@trinity.get('/trinity/v<version:float>/hardwares/<hardware>')
def show_hardware(hardware,version=1):
  req=TrinityAPI(request)
  if not req.is_admin:
    ret={'error':req.not_admin}
    return ret
  hc_overview=req.detailed_overview()
  c_nodes=set()
  for cluster in hc_overview['cluster']:
    c_nodes=c_nodes.union(set(hc_overview['cluster'][cluster]))
  h_overview={}
  h_overview={} 
  h_overview['total']=len(hc_overview['hardware'][hardware])
  h_overview['list_unallocated']=list(set(hc_overview['hardware'][hardware])-c_nodes)
  h_overview['unallocated']=len(h_overview['list_unallocated'])  
  h_overview['allocated']=h_overview['total']-h_overview['unallocated']   
  return h_overview    

@trinity.get('/trinity/v<version:float>/clusters/<cluster>/hardware')
def show_hardware_details(cluster,version=1):
  req=TrinityAPI(request)
  return req.cluster_details(cluster)


# This is used for both create and modify
@trinity.put('/trinity/v<version:float>/clusters/<cluster>')
def modify_cluster(cluster,version=1):
  global state_has_changed
  global all_nodes_info
  global network_map

  state_has_changed=True
  req=TrinityAPI(request)
  ret={}
  ret['statusOK']=True
  clusters=req.detailed_overview()['cluster'].keys()
  if cluster in clusters:
    cluster_exists = True

    ret=update_cluster(req,cluster)
    slurm_needs_update=False
    if ret['statusOK']:
      if ret['change']:
        slurm_needs_update=True
  else:
    cluster_exists = False
    ret=create_cluster(req,cluster)
    if ret['statusOK']:
      # Create the cluster home directories    
      vc_cluster=req.vc + cluster
      cluster_home=os.path.join(req.cluster_path,vc_cluster) 
      if not os.path.isdir(cluster_home):
        os.makedirs(cluster_home) 
      src_root=req.template_dir
      vc_cluster=req.vc + cluster
      dest_root=os.path.join(req.cluster_path,
                             vc_cluster)
      excludes=[]
      copy_with_excludes(src_root,dest_root,excludes)
      # create munge user on the physical node it does not exist
      # then create a munge key
      subprocess.call('! id munge && useradd -u 1002 -U munge',shell=True)
      munge_dir_path=os.path.join(req.cluster_path,vc_cluster,req.munge_key_dir)
      munge_key_path=os.path.join(munge_dir_path,req.munge_key_file)
      if os.path.isfile(munge_key_path):
        os.remove(munge_key_path)
      if not os.path.isdir(munge_dir_path):
        os.makedirs(munge_dir_path)
      subprocess.call('dd if=/dev/urandom bs=1 count=1024 > '+munge_key_path,shell=True)       
      subprocess.call('chown munge:munge '+munge_key_path,shell=True)
      subprocess.call('chmod u=r,go= '+munge_key_path,shell=True)
      subprocess.call('chown munge:munge '+munge_dir_path,shell=True)
      subprocess.call('chmod u=rwx,go= '+munge_dir_path,shell=True)
      subprocess.call('chmod u=rwx,go=rx '+req.cluster_path+'/'+vc_cluster+'/etc/slurm',shell=True) 
      subprocess.call('chmod u=rw,go=rx '+req.cluster_path+'/'+vc_cluster+'/etc/slurm/slurm.conf',shell=True) 
      subprocess.call('chmod u=rw,go=r '+req.cluster_path+'/'+vc_cluster+'/etc/slurm/slurm-nodes.conf',shell=True) 
      subprocess.call('chmod ug=rw,o=r '+req.cluster_path+'/'+vc_cluster+'/etc/slurm/slurm-user.conf',shell=True) 
      slurm_needs_update=True 
 
      apps=os.path.join(req.cluster_path,vc_cluster,'apps')
      modulefiles=os.path.join(req.cluster_path,vc_cluster,'modulefiles')
      if not os.path.isdir(apps):
        os.makedirs(apps)
      if not os.path.isdir(modulefiles):
        os.makedirs(modulefiles)

  if slurm_needs_update:    
    vc_cluster=req.vc + cluster
    slurm=os.path.join(req.cluster_path,
                       vc_cluster,
                       req.slurm_node_file)
    fop=open(slurm,'w')
    nodes = sorted(ret['nodeList'])
    for cont in nodes: 
      node_name=cont
      cpu_count=all_nodes_info[cont]['cpucount']
      slurm_string='NodeName='+node_name+' CPUS='+cpu_count+' State=UNKNOWN'
      fop.write(slurm_string+'\n')
    cont_string=','.join(nodes)
    part_string='PartitionName='+req.cont_part+' Nodes='+cont_string+' Default=Yes MaxTime=INFINITE State=UP'
    fop.write(part_string+'\n')
    fop.close()   
      
  ##---------------------------------------------------------------------
  ## In this part we update makehosts, makedns etc for the cluster
  ##---------------------------------------------------------------------
  vc_cluster=req.vc + cluster
  vc_net='vc_'+cluster+'_net'
  login_cluster='login-'+cluster

  # Get the network info
  path="/tables/networks/rows"
  xcat_networks=requests.get(xcat_host+path,verify=False,params=req.query,headers=req.headers).json()["networks"]
  network_map={}
  for network in xcat_networks:
    if "domain" in network and network["domain"].startswith(req.vc):
      network_map.update({network["domain"]:network["net"].split(".")[1]})
 
  if vc_cluster in network_map.keys():
    second_octet=network_map[vc_cluster]
  else: 
    for second_octet_int in range(16,32):
      second_octet=str(second_octet_int)
      if second_octet not in network_map.values():
        break

  if not cluster_exists :
    # create vc-<cluster> entry in the hosts table
    # The verb is PUT because the nodes already exist
    verb='PUT' 
    path='/tables/hosts/rows/node='+vc_cluster
    payload={
      "ip" : "|\D+(\d+)$|172."+second_octet+".((($1-1)/255)).(($1-1)%255+1)|", 
      "hostnames" : "|\D+(\d+)$|c($1)|"
    }
    req.xcat(verb=verb,path=path,payload=payload)
    verb='PUT'
    # create login-<cluster> entry in the hosts table
    path='/tables/hosts/rows/node='+login_cluster
    payload={
      "ip" : "172."+second_octet+".255.254",
      "hostnames" : "login."+vc_cluster
    }
    req.xcat(verb=verb,path=path,payload=payload)
    # create the entry in the networks table
    verb='POST'
    path='/networks/'+vc_net
    payload={
      "domain" : vc_cluster,
      "gateway" : "<xcatmaster>",
      "mask" : "255.255.0.0",
      "mgtifname" : req.xcat_mgtifname,
      "net" : "172."+second_octet+".0.0"
    }
    req.xcat(verb=verb,path=path,payload=payload)
    # create a login node entry in the xCATdb
    verb='POST'
    path='/nodes/'+login_cluster
    payload={
      "groups" : "login"
    }
    req.xcat(verb=verb,path=path,payload=payload)
    # makehost and makedns for login node
    verb='POST'
    payload={}
    path='/nodes/'+login_cluster+'/host' 
    req.xcat(verb=verb,path=path,payload=payload)
    path='/nodes/'+login_cluster+'/dns' 
    req.xcat(verb=verb,path=path,payload=payload)

  # makehost and makedns for cluster
  cont_subs_list=[]
  node_subs_list=[]
  for cont in ret["subsList"]:
     cont_subs_list.append(cont)
     subtracted_node=cont.replace(req.cont_pref,req.node_pref,1)
     node_subs_list.append(subtracted_node)
  cont_subs_string=",".join(cont_subs_list)
  node_subs_string=",".join(node_subs_list)
  if cont_subs_list:
    verb='DELETE'
    payload={}
    path='/nodes/'+cont_subs_string+'/dns' 
    r=requests.delete(req.xcat_host+path,verify=False,params=req.query)
    verb='POST'
    payload={"command":["docker stop trinity; docker rm trinity"]}
    path='/nodes/'+node_subs_string+'/nodeshell'
    req.xcat(verb=verb,path=path,payload=payload)

  cont_adds_list=[]
  node_adds_list=[]
  for cont in ret["addsList"]:
     cont_adds_list.append(cont)
     added_node=cont.replace(req.cont_pref,req.node_pref,1)
     node_adds_list.append(added_node)
  cont_adds_string=",".join(cont_adds_list)
  node_adds_string=",".join(node_adds_list)

  if cont_adds_list:
    verb='POST'
    payload={}
    path='/nodes/'+cont_adds_string+'/host' 
    req.xcat(verb=verb,path=path,payload=payload)
    path='/nodes/'+cont_adds_string+'/dns' 
    req.xcat(verb=verb,path=path,payload=payload)
    verb='POST'
    payload={"command":["docker stop trinity; docker rm trinity; service trinity restart"]}
    path='/nodes/'+node_adds_string+'/nodeshell'
    req.xcat(verb=verb,path=path,payload=payload)
  state_has_changed=True

  #----------------------------------------------------------------------
  # Now create the login node
  #----------------------------------------------------------------------
  login_ip="172."+second_octet+".255.254"
  returncode=subprocess.call("ping -c 1 "+login_ip, shell=True)
  if returncode != 0:
    login_pool=login_cluster
    path=req.nova_host+'/'+req.tenant_id+'/os-floating-ips-bulk'
    headers={"X-Auth-Project-Id":"admin", "X-Auth-Token":req.token}
    headers.update(req.headers)
    payload={
      "floating_ips_bulk_create":{
        "ip_range":"172."+second_octet+".255.254",
        "pool": login_pool
      }
    }   
    r=requests.post(path,headers=headers,data=json.dumps(payload))
 
    path=req.keystone_admin+'/OS-KSADM/roles'
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.get(path,headers=headers)
    for role in r.json()["roles"]:
      if role["name"] == "_member_":
        role_id=role["id"]
        break

    path=req.keystone_admin+'/users'
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    payload={
      "user": {
        "name": "trinity_dummy_user",
        "email": "",
        "enabled": True,
        "OS-KSADM:password": "system"
      }
    }
    r=requests.post(path,headers=headers,data=json.dumps(payload))

  
    path=req.keystone_admin+'/users'
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.get(path,headers=headers)
    for user in r.json()["users"]:
      if user["username"] == "trinity_dummy_user":
        user_id=user["id"]
        break

  
    path=req.keystone_admin+'/tenants'
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.get(path,headers=headers)
    for tenant in r.json()["tenants"]:
      if tenant["name"] == cluster:
        tenant_id=tenant["id"]
        break

    path=req.keystone_admin+'/tenants/'+tenant_id+'/users/'+user_id+'/roles/OS-KSADM/'+role_id
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.put(path,headers=headers)

    path=req.keystone_host+'/tokens'
    headers=req.headers
    payload = { 
               "auth": {
                 "tenantName": cluster,
                 "passwordCredentials": {
                   "username": "trinity_dummy_user",
                   "password": "system"
                 }
               }
             }
    r = requests.post(path, data=json.dumps(payload), headers=headers)
    tenant_token = r.json()["access"]["token"]["id"]

    path=req.nova_host+'/'+tenant_id+'/os-floating-ips'  
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    payload={
      "pool":login_pool
    } 
    r = requests.post(path, data=json.dumps(payload), headers=headers)
 
    path=req.nova_host+'/'+tenant_id+'/os-security-groups'  
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    r = requests.get(path, headers=headers)
    for security_group in r.json()["security_groups"]:
      if security_group["name"] == "default": 
        default_id=security_group["id"]
        break

    path=req.nova_host+'/'+tenant_id+'/os-security-group-rules'  
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    payload={
      "security_group_rule": {
        "ip_protocol": "tcp", 
        "parent_group_id": default_id, 
        "from_port": 1, 
        "to_port": 65535, 
        "cidr": "0.0.0.0/0", 
        "group_id": None
      }
    }
    r = requests.post(path, data=json.dumps(payload), headers=headers)

    payload={
      "security_group_rule": {
        "ip_protocol": "icmp", 
        "parent_group_id": default_id, 
        "from_port": -1, 
        "to_port": -1, 
        "cidr": "0.0.0.0/0", 
        "group_id": None
      }
    }

    r = requests.post(path, data=json.dumps(payload), headers=headers)

    path=req.nova_host+'/'+tenant_id+'/images'
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    r = requests.get(path, headers=headers)
    for image in r.json()["images"]:
      if image["name"] == "login":
        image_id=image["id"]

    # For now assume that we are using flavor = 2 (small)
    fop=open(req.login_conf)
    login_data=fop.read()
    fop.close()
    replacements={
      "vc-a":vc_cluster,
      "UTC":tzlocal.get_localzone().zone or 'UTC'
    }
    for i,j in replacements.iteritems():
      print i,j
      login_data = login_data.replace(i,j)
    login_data_encoded=base64.b64encode(login_data)
    path=req.nova_host+'/'+tenant_id+'/servers'
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    payload={
      "server":{
        "name":login_cluster,
        "imageRef":image_id,
        "flavorRef": "2",
        "user_data": login_data_encoded,
        "security_groups": [{"name":"default"}],
        "max_count": 1,
        "min_count": 1
      }
    }
    r = requests.post(path, data=json.dumps(payload), headers=headers)
    instance_id=r.json()["server"]["id"]

    # This is added to add a small delay between creating the instance 
    # and associating a floating ip, otherwise we get the following message
    # "No nw_info cache associated with instance"
    time.sleep(5)

    path=req.nova_host+'/'+tenant_id+'/servers/'+instance_id+'/action'
    headers={"X-Auth-Project-Id":cluster, "X-Auth-Token":tenant_token}
    headers.update(req.headers)
    payload={
      "addFloatingIp": {
        "address": "172."+second_octet+".255.254"
      }
    } 
    r = requests.post(path, data=json.dumps(payload), headers=headers)
  
    path=req.keystone_admin+'/tenants/'+tenant_id+'/users/'+user_id+'/roles/OS-KSADM/'+role_id
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.delete(path,headers=headers)
 
    path=req.keystone_admin+'/users/'+user_id
    headers={"X-Auth-Token":req.token}
    headers.update(req.headers)
    r=requests.delete(path,headers=headers)
  return ret


@trinity.get('/trinity/v<version:float>/monitoring')
def show_monitoring_info(version=1):
  req=TrinityAPI(request)
  return req.mon_info()

# Helper functions

def create_cluster(req,cluster):
  old_list=[]
  hw_dict={}
  ret=req.cluster_change_nodes(cluster,old_list,hw_dict)
  return ret

def update_cluster(req,cluster):
  ret={}; ret['statusOK']=False
  r=req.group_nodes(name=cluster,startkey=req.vc) 
  if not r['statusOK']: return ret
  old_list=r['nodes']
  r=req.cluster_details(cluster)
  hw_dict=r['hardware']
  ret=req.cluster_change_nodes(cluster,old_list,hw_dict)
  return ret 

def copy_with_excludes(src_root,dest_root,excludes=[]):
  copy_list=os.listdir(src_root)
  for exclude in excludes:
    if exclude in copy_list:
      copy_list.remove(exclude)
  if not os.path.isdir(dest_root):
    os.makedirs(dest_root) 
  for file in copy_list:
    src=os.path.join(src_root,file)
    dest=os.path.join(dest_root,file)
    if os.path.isdir(src):
      if os.path.isdir(dest):
        shutil.rmtree(dest)
      shutil.copytree(src,dest)
    else:
      shutil.copy2(src,dest)

def replace_lines(conf_file,changes):
  fop=open(conf_file,'r')
  lines=fop.readlines()
  fop.close()
  new_lines=[]
  for line in lines:
    new_line=line.strip()
    for startkey in changes:
      if new_line.startswith(startkey):
        new_line=changes[startkey]
    new_lines.append(new_line) 
  new_conf_file="\n".join(new_lines)
  fop=open(conf_file,'w')
  fop.write(new_conf_file)
  fop.close()

def conf_update(conf_file,key,value,sep='='):
  fop=open(conf_file,'r')
  lines=fop.readlines()
  fop.close()
  new_lines=[]
  for line in lines:
    items=line.strip().split(sep,2)
    new_line=line.strip()
    line_key=items[0].strip()
    if len(items) == 2 and line_key==key: 
      new_line=key+sep+value
    new_lines.append(new_line) 
  new_conf_file="\n".join(new_lines)
  fop=open(conf_file,'w')
  fop.write(new_conf_file)
  fop.close()


def startup():
  global state_has_changed
  global cached_detailed_overview
  global all_nodes_info
  global network_map
  hw='hw-'
  vc='vc-'
  headers={"Content-Type":"application/json", "Accept":"application/json"} # setting this by hand for now
  query = {'userName': trinity_user, 'password': trinity_password, 'userPW': trinity_password }

  # Get the cpucount for all the nodes
  # asuming that all nodes belong to the group compute
  path='/nodes/compute'
  xcat_node_info=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()
  all_nodes_info={}
  for node in xcat_node_info:
    cont=node.replace(node_pref,cont_pref,1)
    all_nodes_info[cont]=xcat_node_info[node]

  path='/groups'
  xcat_groups=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()
  hc_list=[]
  for group in xcat_groups:
    if group.startswith(hw): hc_list.append(group)
    if group.startswith(vc): hc_list.append(group)
  hc_string=",".join(hc_list)
  path='/groups/'+hc_string+'/attrs/members'
  xcat_overview=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()
  hc_overview={'hardware':{},'cluster':{}}
  lhw=len(hw)
  lvc=len(vc)
  for hc in xcat_overview:
    if hc.startswith(hw): 
      hardware=hc[lhw:]
      members=xcat_overview[hc]['members'].strip()
      node_list=[]
      if members: node_list=[x.strip() for x in members.split(',')]
      hc_overview['hardware'][hardware]=node_list
    if hc.startswith(vc): 
      cluster=hc[lvc:]
      members=xcat_overview[hc]['members'].strip()
      node_list=[]
      if members: node_list=[x.strip() for x in members.split(',')]
      hc_overview['cluster'][cluster]=node_list
  cached_detailed_overview=hc_overview

  # Get the network info
  path="/tables/networks/rows"
  xcat_networks=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()["networks"]
  network_map={}
  for network in xcat_networks:
    if "domain" in network and network["domain"].startswith(vc):
      second_octet=network["net"].split(".")[1]      
      network_map.update({second_octet:network["domain"]})

  state_has_changed=False
  trinity.run(host=trinity_host, port=trinity_port, debug=trinity_debug, server=trinity_server)
  

if __name__=="__main__":
   startup()
