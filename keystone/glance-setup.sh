#! /usr/bin/env bash
IP=controller
KS_CONT="keystone"
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-create --name glance --pass system 
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 user-role-add --user glance --tenant service --role admin
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-create --name glance --type image --description "OpenStack Image Service"
SERVICE_ID=$(docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 service-list | awk '/ image / {print $2}')
docker exec ${KS_CONT} keystone --os-token system --os-endpoint http://${IP}:35357/v2.0 endpoint-create --service-id "${SERVICE_ID}" --publicurl http://${IP}:9292 --internalurl http://${IP}:9292 --adminurl http://${IP}:9292 --region regionOne
