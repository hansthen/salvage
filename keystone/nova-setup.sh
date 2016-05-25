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
       --publicurl http://controller:8774/v2/%\(tenant_id\)s \
       --internalurl http://controller:8774/v2/%\(tenant_id\)s \
       --adminurl http://controller:8774/v2/%\(tenant_id\)s \
       compute
