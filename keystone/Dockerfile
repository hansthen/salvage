FROM centos:centos7
MAINTAINER abhishek.mukherjee@clustervision.com
RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
ADD rdo-juno-release.repo /etc/yum.repos.d/rdo-juno-release.repo
RUN yum -y -q install --setopt=tsflags=nodocs epel-release
RUN yum -y -q install --setopt=tsflags=nodocs openstack-selinux openstack-utils openstack-keystone python-keystoneclient && \
    yum -y -q install --setopt=tsflags=nodocs python-pip && \
    yum -y update && yum clean all
VOLUME /var/lib/keystone
RUN pip install supervisor

EXPOSE 5000 35357
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
COPY rootimg /
