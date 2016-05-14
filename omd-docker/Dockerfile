FROM centos:latest

RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install epel-release wget which
RUN yum install -y --nogpgcheck http://files.omdistro.org/releases/centos_rhel/omd-1.20.rhel7.x86_64.rpm
RUN yum install -y --nogpgcheck omd-1.20.rhel7.x86_64.rpm
RUN omd create monitoring
RUN omd config monitoring set DEFAULT_GUI check_mk
RUN omd config monitoring set APACHE_TCP_PORT 5003
RUN omd config monitoring set APACHE_TCP_ADDR $(hostname -I | awk '{print $1}')
RUN omd config monitoring set TMPFS off
RUN omd config monitoring set CRONTAB off
# Accept connections on any IP address, since we get a random one
RUN omd config monitoring set APACHE_TCP_ADDR 0.0.0.0
RUN su - monitoring -c "htpasswd -b ~/etc/htpasswd admin system"
RUN su - monitoring -c "htpasswd -D ~/etc/htpasswd omdadmin"
ADD users.mk "/omd/sites/monitoring/etc/check_mk/multisite.d/wato/users.mk"
ADD hashlib.patch /
RUN patch -p0 < hashlib.patch
RUN chown monitoring:monitoring "/omd/sites/monitoring/etc/check_mk/multisite.d/wato/users.mk"
ADD docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/bash"]
VOLUME /opt/omd
