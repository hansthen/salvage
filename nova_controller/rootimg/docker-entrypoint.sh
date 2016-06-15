#!/bin/bash
chown -R nova:nova /var/log/nova
chown nova:nova /etc/nova/nova.conf
chown -R nova:nova /var/lib/nova
su -s /bin/sh -c "nova-manage db sync" nova
exec "$@"
