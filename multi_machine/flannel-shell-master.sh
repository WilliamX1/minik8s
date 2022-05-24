sudo ./etcd/etcdctl cluster-health

sudo chmod 755 flanneld
sudo ./etcd/etcdctl set /coreos.com/network/config < ./flannel-network-config.json
nohup sudo ./flanneld -iface=192.168.1.9 &
ifconfig docker0

# Restart docker daemon with flannel network
sudo systemctl stop docker.socket
sudo systemctl stop docker
sudo docker ps
source /run/flannel/subnet.env
sudo ifconfig docker0 ${FLANNEL_SUBNET}
sudo dockerd --bip=${FLANNEL_SUBNET} --mtu=${FLANNEL_MTU} &
sudo iptables -P FORWARD ACCEPT