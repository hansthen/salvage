FROM centos:centos7
MAINTAINER abhishek.mukherjee@clustervision.com

RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install --setopt=tsflags=nodocs epel-release && \
    yum -y -q install --setopt=tsflags=nodocs https://repos.fedorapeople.org/repos/openstack/EOL/openstack-juno/rdo-release-juno-1.noarch.rpm
RUN sed -i "/^baseurl/s/openstack-juno/EOL\/openstack-juno/" /etc/yum.repos.d/rdo-release.repo
RUN yum -y -q install --setopt=tsflags=nodocs openstack-selinux openstack-utils openstack-glance python-glanceclient && \
    yum -y -q install --setopt=tsflags=nodocs python-pip && \
    yum -y update && yum clean all

RUN pip install supervisor
VOLUME /var/lib/glance

EXPOSE 9191 9292
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
COPY rootimg /
#COPY docker-entrypoint.sh /
#COPY supervisord.conf /etc/supervisord.conf
#COPY glance-api.conf /etc/glance/glance-api.conf
#COPY glance-registry.conf /etc/glance/glance-registry.conf
