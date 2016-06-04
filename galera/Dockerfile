FROM centos:latest
MAINTAINER hans.then@clustervision.com

COPY galera.repo /etc/yum.repos.d/
# Install required packages and MariaDB Vendor Repo
RUN yum -y update && yum clean all && yum -y install epel-release && \
    groupadd -r mysql && useradd -r -g mysql mysql && \
    yum -y install galera-3 galera-arbitrator-3 percona-xtrabackup-24 \
    mysql-wsrep-5.6 lsof less which socat pwgen && yum clean all

COPY my.cnf /etc/mysql/my.cnf
COPY docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
VOLUME /var/lib/mysql

