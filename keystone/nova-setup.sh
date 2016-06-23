#! /usr/bin/env bash
#------------------------------------------------------------------
# Setup nova service
#------------------------------------------------------------------
obol -H ldap://controller -w system user add nova --password system --cn nova --sn nova --givenName nova
KEYSTONE="docker exec keystone openstack \
       --os-token system \
       --os-url http://controller:35357/v2.0"

$KEYSTONE role add --project service --user nova admin

$KEYSTONE \
       service create --name nova \
       --description "OpenStack Compute service" compute

$KEYSTONE \
       endpoint create --region regionOne \
       --publicurl http://controller:8774/v2/%\(tenant_id\)s \
       --internalurl http://controller:8774/v2/%\(tenant_id\)s \
       --adminurl http://controller:8774/v2/%\(tenant_id\)s \
       compute
