#! /usr/bin/env bash
IP=controller
KS_CONT="keystone"
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-create --name nova --pass system
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-role-add --user nova --tenant service --role admin
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-create --name nova --type compute --description "OpenStack Compute"
SERVICE_ID=$(docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-list | awk '/ compute / {print $2}')
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 endpoint-create --service-id "${SERVICE_ID}" --publicurl http://${IP}:8774/v2/%\(tenant_id\)s --internalurl http://${IP}:8774/v2/%\(tenant_id\)s --adminurl http://${IP}:8774/v2/%\(tenant_id\)s --region regionOne

