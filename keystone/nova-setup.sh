#! /usr/bin/env bash
#------------------------------------------------------------------
# Setup nova service
#------------------------------------------------------------------
KEYSTONE="docker exec keystone openstack \
       --os-token system \
       --os-url http://controller:35357/v2.0"

$KEYSTONE \
       user create \
       --domain default \
       --password system \
       nova

$KEYSTONE role add --project service --user nova admin

$KEYSTONE \
       service create --name nova \
       --description "OpenStack Compute service" compute

$KEYSTONE \
       endpoint create --region RegionOne \
       compute public http://controller:8774/v2/%\(tenant_id\)s

$KEYSTONE \
       endpoint create --region RegionOne \
       compute internal http://controller:8774/v2/%\(tenant_id\)s

$KEYSTONE \
       endpoint create --region RegionOne \
       compute admin http://controller:8774/v2/%\(tenant_id\)s
