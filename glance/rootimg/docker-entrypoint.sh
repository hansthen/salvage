#!/bin/bash

chown glance:glance /etc/glance/glance-api.conf
chown glance:glance /etc/glance/glance-registry.conf
chown -R glance:glance /var/lib/glance
su -s /bin/sh -c "glance-manage db_sync" glance

exec "$@"
