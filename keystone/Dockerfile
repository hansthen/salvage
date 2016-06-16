FROM centos:centos7
MAINTAINER abhishek.mukherjee@clustervision.com
RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install --setopt=tsflags=nodocs epel-release && \ 
    yum -y -q install --setopt=tsflags=nodocs centos-release-openstack-liberty && \
    yum -y -q install --setopt=tsflags=nodocs openstack-selinux openstack-utils openstack-keystone python-openstackclient && \ 
    yum -y -q install --setopt=tsflags=nodocs python-pip && \
    yum -y update && yum clean all
VOLUME /var/lib/keystone
RUN pip install supervisor

EXPOSE 5000 35357
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
COPY rootimg /
