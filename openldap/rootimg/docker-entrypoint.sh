#!/bin/bash
. /var/lib/asynchronous.bash

if [[ ! -d /etc/openldap/slapd.d/cn=config ]]; then
    slaptest -v -f /etc/openldap/slapd.conf -F /etc/openldap/slapd.d
fi
chown -R ldap.ldap /var/lib/ldap
chown -R ldap.ldap /etc/openldap/slapd.d

after nc localhost 389 \< /dev/null <<END
if [[ -d /startup.d ]]; then
    for f in /startup.d/*.sh; do
        . "\$f"
    done
    for f in /startup.d/*.ldif; do
        echo \$f /var/log/startup.log
        ldapmodify -a -x -D cn=Manager,dc=local -w system -f "\$f" >> /var/log/startup.log 2>&1
    done
fi
END

exec "$@"
