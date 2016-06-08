#! /usr/bin/env bash
#------------------------------------------------------------------
# Setup glance service
#------------------------------------------------------------------
KEYSTONE="docker exec keystone openstack \
       --os-token system \
       --os-url http://controller:35357/v2.0"

$KEYSTONE \
       user create \
       --password system \
       glance

$KEYSTONE role add --project service --user glance admin

$KEYSTONE \
       service create --name glance \
       --description "OpenStack Image service" image

$KEYSTONE \
       endpoint create --region regionOne \
       --publicurl http://controller:9292 \
       --internalurl http://controller:9292 \
       --adminurl http://controller:9292 \
       image

