#!/bin/bash
. /var/lib/asynchronous.bash

if [[ ! -d /etc/openldap/slapd.d/cn=config ]]; then
    if [[ -z "$PASSWORD" ]]; then
        PASSWORD=$(date|md5sum|cut -c1-30)
    fi
    echo "$PASSWORD" > /password
    chmod 600 /password
    sed -i -e "s/rootpw.*$/rootpw ${PASSWORD}/" /etc/openldap/root.conf
    slaptest -v -f /etc/openldap/slapd.conf -F /etc/openldap/slapd.d
else
    echo "found previous configuration, will not overwrite"
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
        ldapmodify -a -Y EXTERNAL -H ldapi:/// -f "\$f" >> /var/log/startup.log 2>&1
    done
fi
END

exec "$@"
