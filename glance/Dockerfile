FROM centos:centos7
MAINTAINER abhishek.mukherjee@clustervision.com

RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install --setopt=tsflags=nodocs epel-release && \ 
    yum -y -q install --setopt=tsflags=nodocs centos-release-openstack-liberty && \
    yum -y -q install --setopt=tsflags=nodocs openstack-selinux openstack-utils openstack-glance python-glanceclient && \ 
    yum -y -q install --setopt=tsflags-nodocs python-pip && \
    yum -y update && yum clean all

RUN pip install supervisor
VOLUME /var/lib/glance

EXPOSE 9191 9292
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
COPY rootimg /
