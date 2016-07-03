FROM centos:latest
MAINTAINER hicham.amrati@clustervision.com

RUN yum -y install openldap-servers openldap-clients nc
RUN cp /usr/share/openldap-servers/DB_CONFIG.example /var/lib/ldap/DB_CONFIG
RUN mkdir /var/lib/ldap-2
RUN cp /usr/share/openldap-servers/DB_CONFIG.example /var/lib/ldap-2/DB_CONFIG
RUN chown -R ldap.ldap /var/lib/ldap-2

COPY rootimg /
RUN chown -R ldap. /etc/openldap/ && \
    rm -rf /etc/openldap/slapd.d/* && \
    chmod 600 /etc/openldap/{slapd,local,repl,meta}.conf /etc/openldap/certs/ssl/key

ADD https://raw.githubusercontent.com/hansthen/asynchronous.bash/master/asynchronous.bash /var/lib/asynchronous.bash

RUN mkdir /startup.d
VOLUME /var/lib/ldap
VOLUME /var/lib/ldap-2

EXPOSE 389
EXPOSE 636

RUN chmod +x /docker-entrypoint.sh

CMD ["slapd", "-u", "ldap", "-h", "ldapi:/// ldap:///", "-d1"]
ENTRYPOINT ["/docker-entrypoint.sh"]
