import re
import api
import json
import requests
import ManageCluster
from ConfigParser import SafeConfigParser
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
  req=api.TrinityAPI(request)
  if req.has_access:
    response.status=200
    return {'token': req.token}
  else:
    response.status=401
    return

@trinity.get('/trinity/v<version:float>/overview')
def total_overview(version=1):
  req=api.TrinityAPI(request)
  if not req.is_admin:
    ret={'error':req.not_admin}
    return ret
  return req.detailed_overview()
 

@trinity.get('/trinity/v<version:float>/overview/hardwares')
def hardware_overview(version=1):
  req=api.TrinityAPI(request)
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
  req=api.TrinityAPI(request)
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
  req=api.TrinityAPI(request)
  clusters=req.detailed_overview()['cluster'].keys()
  return {'statusOK': True, 'clusters': clusters}

@trinity.get('/trinity/v<version:float>/hardwares')
def list_hardwares(version=1):
  req=api.TrinityAPI(request)
  hardwares=req.detailed_overview()['hardware'].keys()
  return {'statusOK': True, 'hardwares': hardwares}

@trinity.get('/trinity/v<version:float>/nodes')
def list_nodes(version=1):
  req=api.TrinityAPI(request)
  return req.nodes()

@trinity.get('/trinity/v<version:float>/nodes/<node>')
def show_node(node,version=1):
  req=api.TrinityAPI(request)
  # We do an authentication here because the object method is 
  # need by non-admin calls too
  req.authenticate()
  if req.is_admin:
    return req.node_info(node)
  else:
    return {'error':req.not_admin}

@trinity.get('/trinity/v<version:float>/clusters/<cluster>')
def show_cluster(cluster,version=1):
  req=api.TrinityAPI(request)
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
  req=api.TrinityAPI(request)
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
  req=api.TrinityAPI(request)
  return req.cluster_details(cluster)


# This is used for both create and modify
@trinity.put('/trinity/v<version:float>/clusters/<cluster>')
def modify_create(cluster,version=1):
    mod=ManageCluster.Modify(cluster,version=1)
    return mod.modify_cluster(cluster,version=1)

@trinity.get('/trinity/v<version:float>/monitoring')
def show_monitoring_info(version=1):
  req=api.TrinityAPI(request)
  return req.mon_info()

########################################################################
def startup():
  hw='hw-'
  vc='vc-'
  headers={"Content-Type":"application/json", "Accept":"application/json"} # setting this by hand for now
  query = {'userName': trinity_user, 'password': trinity_password, 'userPW': trinity_password }

  # Get the cpucount for all the nodes
  # asuming that all nodes belong to the group compute
  path='/nodes/compute'
  xcat_node_info=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()
  api.all_nodes_info={}
  for node in xcat_node_info:
    cont=node.replace(node_pref,cont_pref,1)
    api.all_nodes_info[cont]=xcat_node_info[node]

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
  api.cached_detailed_overview=hc_overview

  # Get the network info
  path="/tables/networks/rows"
  xcat_networks=requests.get(xcat_host+path,verify=False,params=query,headers=headers).json()["networks"]
  network_map={}
  for network in xcat_networks:
    if "domain" in network and network["domain"].startswith(vc):
      second_octet=network["net"].split(".")[1]      
      network_map.update({second_octet:network["domain"]})

  api.state_has_changed=False
  trinity.run(host=trinity_host, port=trinity_port, debug=trinity_debug, server=trinity_server)
  

if __name__=="__main__":
   startup()
