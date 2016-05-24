FROM centos:centos7
MAINTAINER abhishek.mukherjee@clustervision.com

RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
ADD rdo-juno-release.repo /etc/yum.repos.d/rdo-juno-release.repo
RUN yum -y -q install --setopt=tsflags=nodocs epel-release
    yum -y -q install --setopt=tsflags=nodocs openstack-selinux openstack-utils && \
    yum -y -q install --setopt=tsflags=nodocs openstack-nova-api openstack-nova-cert openstack-nova-conductor \
                                           openstack-nova-console openstack-nova-novncproxy openstack-nova-scheduler \
                                           python-novaclient && \ 
    yum -y -q install --setopt=tsflags=nodocs python-pip && \
    yum -y update && yum clean all
VOLUME /var/lib/nova
RUN pip install supervisor

EXPOSE 8773 8774 8775 3333 6080 5800 5900 
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
COPY docker-entrypoint.sh /
COPY nova.conf /etc/nova/nova.conf
COPY supervisord.conf /etc/supervisord.conf
