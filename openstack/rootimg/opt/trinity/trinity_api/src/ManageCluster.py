import re
import os
import api
import json
import time
import shutil
import base64
import tzlocal
import requests
import subprocess
from retrying import retry
from ConfigParser import SafeConfigParser
from novaclient import client as novaclient
from bottle import Bottle,get,put,post,delete,run,request,response,abort

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
keystone_admin_user=config.get('keystone', 'keystone_admin_user')
keystone_admin_pass=config.get('keystone', 'keystone_admin_pass')

# This is used for both create and modify
class Modify (object):
 def __init__(self,cluster,version=1):
  self.version=version
  self.cluster=cluster

 def modify_cluster(self,cluster,version=1):
  
  global network_map
  api.state_has_changed=True
  req=api.TrinityAPI(request)
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
    @retry(stop_max_delay=10000,wait_fixed=1000)
    def try_write():
      fop=open(slurm,'w')
      nodes = sorted(ret['nodeList'])
      for cont in nodes:
        node_name=cont
        cpu_count=api.all_nodes_info[cont]['cpucount']
        slurm_string='NodeName='+node_name+' CPUS='+cpu_count+' State=UNKNOWN'
        fop.write(slurm_string+'\n')
      cont_string=','.join(nodes)
      part_string='PartitionName='+req.cont_part+' Nodes='+cont_string+' Default=Yes MaxTime=INFINITE State=UP'
      fop.write(part_string+'\n')
      fop.close()
    try_write()
    subprocess.call('echo slurm-nodes.conf was written',shell=True) 

      
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
  if 'error' not in ret:
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
  if 'error' not in ret:
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
   api.state_has_changed=True

  #----------------------------------------------------------------------
  # Now create the login node
  #----------------------------------------------------------------------
  
  login_ip="172."+second_octet+".255.254"
  nova = novaclient.Client('2', keystone_admin_user, keystone_admin_pass, 
                           'admin',req.keystone_host, connection_pool=True)
  if not nova.servers.list(search_opts={'all_tenants': 1, 'name': 'login-' + cluster}):
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
    r=requests.get(path,headers=headers)
    for user in r.json()["users"]:
      if user["username"] == "trinity":
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
                   "username": 'trinity',
                   "password": 'system'
                 }
               }
             }
    r = requests.post(path, data=json.dumps(payload), headers=headers)
    tenant_token =r.json()["access"]["token"]["id"]

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
        "flavorRef": "448f9710-f5b5-454c-b89a-fc8d691d9d87",
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
 
  return ret


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
