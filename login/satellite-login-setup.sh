#! /bin/bash
#title          : create a satellite login node
#description    : Template script to be passed as userdata for satellite login node creation
#author         : Hans Then, Abhishek Mukherjee
#email          : hans.then@clustervision.com
                  abhishek.mukherjee@clustervision.com

cluster=vc-a

#---------------------------------------------------------------------------
# Enable password authenication
#---------------------------------------------------------------------------
echo "system" | passwd root --stdin
sed -e 's/[#]*PasswordAuthentication no/PasswordAuthentication yes/g' -i /etc/ssh/sshd_config
service sshd restart


#-------------------------------------------------------------------------
# Wait until the floating ip is up
#-------------------------------------------------------------------------
controller="10.141.255.254"
access=1;
while [ ${access} -ne "0" ];
   do ping -c 1 ${controller} ; access=$? ; sleep 1;
done


#--------------------------------------------------------------------------
# Copy the required files from controller to the login node
#--------------------------------------------------------------------------
mkdir -p /trinity
mount ${controller}:/trinity /trinity
cp -LrT /trinity/login/rootimg /

# Make sure that /tmp is world writable
chmod -R 777 /tmp
chmod +t /tmp

#---------------------------------------------------------------------------
# Setup NFS mounts
#---------------------------------------------------------------------------
cat <<EOF >> /etc/fstab
controller:/cluster/${cluster} /cluster nfs rsize=8192,wsize=8192,timeo=14,intr
controller:/trinity /trinity nfs rsize=8192,wsize=8192,timeo=14,intr
controller:/home/${cluster} /home nfs rsize=8192,wsize=8192,timeo=14,intr
EOF

umount ${controller}:/trinity

for in in {1..10}; do
   error=$(mount -a 2>&1)
   if [[ -z "$error" ]]; then break; fi
   echo "mount -a failed: retrying"
   sleep 10
done
error=$(mount -a 2>&1)
if [[ ! -z "$error" ]]; then
   echo "ERROR: failure to mount file systems."
fi

#---------------------------------------------------------------------------
# Synchronize munge keys.
#---------------------------------------------------------------------------
sudo -u munge cp /cluster/etc/munge/munge.key /etc/munge/munge.key

cat << EOF > /etc/resolv.conf
search cluster. ${cluster}. cluster
nameserver 10.141.255.254
EOF

#---------------------------------------------------------------------------
# Configure LDAP
#---------------------------------------------------------------------------
yum -y -q install nss-pam-ldapd authconfig

# append our config to the ldap nameserver demon
cat > /etc/nslcd.conf << EOF
uri ldap://login
ssl no
tls_cacertdir /etc/openldap/cacerts
base group  ou=Group,dc=cluster
base passwd ou=People,dc=cluster
base shadow ou=People,dc=cluster
EOF

# setup nssswitch
sed -e 's/^group:.*$/group:\t\tfiles ldap/g' \
    -e 's/^passwd:.*$/passwd:\t\tfiles ldap/g' \
    -e 's/^shadow:.*$/shadow:\t\tfiles ldap/g' \
    -i /etc/nsswitch.conf

authconfig-tui --kickstart --enableldapauth --ldapbasedn=dc=local \
     --ldapserver=login

systemctl stop slurm

curl http://169.254.169.254/openstack/latest/meta_data.json > /root/meta_data.json

