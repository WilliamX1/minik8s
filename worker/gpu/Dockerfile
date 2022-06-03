FROM ubuntu
MAINTAINER xxx <user@example.org>

# update ubuntu repository
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update

# install ubuntu packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip expect openssh-client

RUN pip install flask

# define a mount point
#RUN #ssh-keygen -q -t rsa -N '' -f /id_rsa
ADD upload.sh upload.sh
ADD instance_name/data/ /data/

EXPOSE 5052

# define command for this image
#CMD ["/bin/bash", "a.sh"]
#CMD ["python3","/serverless_server.py"]
