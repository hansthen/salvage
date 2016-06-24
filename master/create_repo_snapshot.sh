#!/bin/bash
set -x
OSTACKRELEASE="centos-openstack-liberty"
DATE=$(date +%Y%m%d)
set +x
if ! grep -Fq $OSTACKRELEASE /etc/yum.repos.d/*.repo; then
    echo "Please check that your rdo-release package matches the $OSTACKRELEASE distribution!"
    exit 1
fi
set -x
mkdir -p /install/post/$DATE/centos7/x86_64
if [ -d /install/post/otherpkgs/centos7/x86_64/ ]; then
    # Make a copy of the current repo, to avoid that the reposync command that follows 
    #  downloads again stuff that was already in the old repo 
    cp -rl /install/post/otherpkgs/centos7/x86_64/* /install/post/$DATE/centos7/x86_64
    # Remove the symlink
    rm /install/post/otherpkgs
fi
reposync -n -r epel -r base -r extras -r updates -r xcat-2-core -r xcat-dep \
            -r elrepo -r $OSTACKRELEASE -p /install/post/$DATE/centos7/x86_64/
# Sync the repo that is in the $DATE directory, downloading only what is missing (faster)
ln -sT /install/post/$DATE /install/post/otherpkgs
mkdir -p /install/post/otherpkgs/centos7/x86_64/check_mk
cd /install/post/otherpkgs/centos7/x86_64/check_mk
wget -c https://mathias-kettner.de/download/check_mk-agent-1.2.4p5-1.noarch.rpm
wget -c https://mathias-kettner.de/download/check_mk-agent-logwatch-1.2.4p5-1.noarch.rpm
cd -
createrepo /install/post/otherpkgs/centos7/x86_64/


