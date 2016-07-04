FROM centos:latest
MAINTAINER hans.then@gmail.com

RUN yum -y install openldap-servers openldap-clients nc epel-release
RUN cp /usr/share/openldap-servers/DB_CONFIG.example /var/lib/ldap/DB_CONFIG
RUN yum -y install python-pip && pip install obol

COPY rootimg /
RUN chown -R ldap. /etc/openldap/ && \
    rm -rf /etc/openldap/slapd.d/* && \
    chmod 600 /etc/openldap/{slapd,local,repl,meta}.conf /etc/openldap/certs/ssl/key

ADD https://raw.githubusercontent.com/hansthen/asynchronous.bash/master/asynchronous.bash /var/lib/asynchronous.bash

RUN mkdir /startup.d
VOLUME /var/lib/ldap

EXPOSE 389
EXPOSE 636

RUN chmod +x /docker-entrypoint.sh

CMD ["slapd", "-u", "ldap", "-h", "ldapi:/// ldap:///", "-d1"]
ENTRYPOINT ["/docker-entrypoint.sh"]
