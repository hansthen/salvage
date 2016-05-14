FROM centos:latest
MAINTAINER hans.then@clustervision.com
RUN yum -y swap -- remove systemd-container* -- install systemd systemd-libs
RUN yum -y -q install epel-release iproute
RUN yum -y -q groupinstall "Infiniband Support"

RUN useradd munge -u 1002 -U && useradd slurm -u 1001 -U && \
    mkdir /var/run/slurm /var/spool/slurm /var/log/slurm && \
    mkdir -m 755 -p /var/run/munge && \
    chown munge:munge /var/run/munge

RUN yum -y -q install openssh-server openssh-clients python-pip vim-minimal \
    infiniband-diags munge rsyslog bind-utils perl perl-DBI perl-Switch \
    openldap-clients nss-pam-ldapd authconfig environment-modules \
    infinipath-psm iproute \
    xauth xorg-x11-xauth \
    vim-enhanced \
    hostname && yum clean all

RUN mkdir -p /var/run/sshd && \
    chmod -rx /var/run/sshd && \
    ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key && \
    ssh-keygen -t dsa -f /etc/ssh/ssh_host_dsa_key && \
    sed -i -e 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/g' \
           -e 's/AcceptEnv XMODIFIERS/AcceptEnv TZ XMODIFIERS/g' \
        /etc/ssh/sshd_config

RUN rm /etc/rsyslog.d/listen.conf && \
    sed -i "s/^\$OmitLocalLogging on/#\$OmitLocalLogging on/" \
     /etc/rsyslog.conf

RUN pip install supervisor
COPY rootimg /

ADD rpms /rpms
RUN yum install -y /rpms/*.rpm

RUN chmod +x /docker-entrypoint.sh

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
ENTRYPOINT ["/docker-entrypoint.sh"]

RUN yum -y -q install numactl numactl-devel \
    glibc-devel kernel-headers kernel-tools \
    pciutils bc less libsysfs-devel libibverbs-devel \
    libgfortran && yum clean all

