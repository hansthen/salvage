#!/bin/bash

set -x
cat ../controller/rootimg/install/custom/install/centos/*pkg* \
    ../controller/rootimg/install/custom/netboot/centos/*pkg* \
    | grep -v ^# | grep -v ^$ | grep -v ^@ | sort -u > /tmp/pkglist
cat ../controller/rootimg/install/custom/install/centos/*pkg* \
    ../controller/rootimg/install/custom/netboot/centos/*pkg* \
    | grep ^@ | sort -u > /tmp/grplist
mkdir -p /install/post/otherpkgs/centos7/x86_64/Packages
cat /tmp/pkglist | xargs repotrack -p /install/post/otherpkgs/centos7/x86_64/Packages
cat /tmp/grplist | sed 's,@ ,@,' | \
    xargs yumdownloader --resolve --destdir /install/post/otherpkgs/centos7/x86_64/Packages
createrepo /install/post/otherpkgs/centos7/x86_64/
