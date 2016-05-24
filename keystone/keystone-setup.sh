#! /usr/bin/env bash
KS_CONT="keystone"
docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       tenant-create --description "Admin Tenant" \
       admin

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       user create --pass system \
       admin

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       role create \
       admin

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       role add --user admin \
       --project admin \
       admin

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       project create --description "Service Tenant" \
       service

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       service create \
       --name keystone \
       --description "OpenStack Identity" \
       identity

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       endpoint create \
       --publicurl http://controller:5000/v2.0 \
       --internalurl http://controller:5000/v2.0 \
       --adminurl http://controller:35357/v2.0 \
       --region regionOne \
       keystone
