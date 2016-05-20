#! /usr/bin/env bash
KS_CONT="keystone"
docker exec ${KS_CONT} os 
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       user create --password system \ 
       nova

docker exec ${KS_CONT} os \
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       role add --user nova --project service \
       admin

docker exec ${KS_CONT} os
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 \
       service-create --name nova \
       --description "OpenStack Compute Service" \
       compute

docker exec ${KS_CONT} os
       --os-token system \
       --os-endpoint http://controller:35357/v2.0 endpoint create \
       --publicurl http://controller:8774/v2/%\(tenant_id\)s \
       --internalurl http://controller:8774/v2/%\(tenant_id\)s \
       --adminurl http://controller:8774/v2/%\(tenant_id\)s \
       --region regionOne \
       compute

