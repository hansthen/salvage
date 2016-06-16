#! /usr/bin/env bash
sleep 10s
#------------------------------------------------------------------
# Setup a helper variable
#------------------------------------------------------------------
KEYSTONE="docker exec keystone openstack \
       --os-token system \
       --os-url http://controller:35357/v2.0"

#------------------------------------------------------------------
# First create the endpoints. We use the administrative URL for this.
# http://docs.openstack.org/liberty/install-guide-rdo/keystone-services.html
# This documentation does not work very well, the commandline API turns out to 
# be different than what's documented.
#------------------------------------------------------------------
$KEYSTONE \
       service create \
       --name keystone \
       --description "OpenStack Identity" \
       identity

$KEYSTONE \
       endpoint create \
       --region regionOne \
       --publicurl http://controller:5000/v2.0 \
       --internalurl http://controller:5000/v2.0 \
       --adminurl http://controller:35357/v2.0 \
       identity

#------------------------------------------------------------------
# Next we create users and roles for the administrative user and tenant/
# In http://docs.openstack.org/liberty/install-guide-rdo/keystone-users.html
#------------------------------------------------------------------
# section 1

obol -H ldap://controller -w system user add "admin" --password system --cn "admin" --sn "admin" --givenName "admin"
obol -H ldap://controller -w system user add "trinity" --password system --cn "trinity" --sn "trinity" --givenName "trinity"

$KEYSTONE \
       project create \
       --description "Admin Project" \
       admin

$KEYSTONE \
       role create \
       admin

$KEYSTONE \
       role create \
       _member_

$KEYSTONE \
       role add --project admin --user admin \
       admin

# section 2
$KEYSTONE \
       project create \
       --description "Service Project" \
       service

# We skip section 3 from the openstack manual
# which would be the creation of a demo tenant

