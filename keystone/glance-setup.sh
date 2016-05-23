#! /usr/bin/env bash
KS_CONT="keystone"
docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       user create --password system \ 
       glance

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       role add --user glance --project service \
       admin

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       service-create --name glance \
       --description "OpenStack Image Service" \
       image

docker exec ${KS_CONT} openstack \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 endpoint create \
       --publicurl http://controller:8774/v2/%\(tenant_id\)s \
       --internalurl http://controller:8774/v2/%\(tenant_id\)s \
       --adminurl http://controller:8774/v2/%\(tenant_id\)s \
       --region regionOne \
       compute

