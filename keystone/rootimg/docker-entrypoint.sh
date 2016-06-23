#!/bin/bash

if [[ ! -d /etc/keystone/ssl ]]; then
    keystone-manage pki_setup --keystone-user keystone --keystone-group keystone
    chown -R keystone:keystone /var/log/keystone
    chown -R keystone:keystone /etc/keystone/ssl
    chmod -R o-rwx /etc/keystone/ssl
    chown keystone:keystone /etc/keystone/keystone.conf
    chown -R keystone:keystone /var/lib/keystone
    su -s /bin/sh -c "/usr/bin/keystone-manage db_sync" keystone
fi

exec "$@"
