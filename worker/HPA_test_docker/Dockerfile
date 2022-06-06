FROM ubuntu
MAINTAINER xxx <user@example.org>

# update ubuntu repository
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update

# install ubuntu packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip

RUN pip install flask -i https://pypi.douban.com/simple

# define a mount point
ADD test_server.py test_server.py

EXPOSE 5053

# define command for this image
CMD ["python3","/test_server.py"]