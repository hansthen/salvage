#! /usr/bin/env bash
sleep 10s
echo ; docker ps
IP=10.141.255.254
KS_CONT="keystone"
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 tenant-create --name admin --description "Admin Tenant"
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-create --name admin --pass system 
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 role-create --name admin
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-role-add --user admin --tenant admin --role admin
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 tenant-create --name service --description "Service Tenant"
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-create --name keystone --type identity --description "OpenStack Identity"
SERVICE_ID=$(docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-list | awk '/ identity / {print $2}')
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 endpoint-create --service-id "${SERVICE_ID}" --publicurl http://${IP}:5000/v2.0 --internalurl http://${IP}:5000/v2.0 --adminurl http://${IP}:35357/v2.0 --region regionOne
