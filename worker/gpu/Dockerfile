FROM ubuntu
MAINTAINER xxx <user@example.org>

# update ubuntu repository
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update

# install ubuntu packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip expect openssh-client

RUN pip install flask

# define a mount point
#RUN #ssh-keygen -q -t rsa -N '' -f /id_rsa
ADD ./data/ /data/
ADD ./upload.sh /upload.sh
ADD ./download.sh /download.sh
ADD ./gpu_server.py /gpu_server.py


EXPOSE 5054

# define command for this image
#CMD ["/bin/bash", "a.sh"]
CMD ["python3","/gpu_server.py"]
