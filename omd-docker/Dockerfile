FROM centos:latest

RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install epel-release wget which
RUN yum install -y --nogpgcheck http://files.omdistro.org/releases/1.30/omd-1.30.rhel7.x86_64.rpm
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
RUN chown monitoring:monitoring "/omd/sites/monitoring/etc/check_mk/multisite.d/wato/users.mk"
RUN cp /usr/lib64/python2.7/hashlib.py /omd/versions/1.30/lib/python/hashlib.py
ADD docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/bin/bash"]
VOLUME /opt/omd
