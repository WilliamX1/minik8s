FROM ubuntu
MAINTAINER xxx <user@example.org>

# update ubuntu repository
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update

# install ubuntu packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip

# install python requirements
RUN pip install flask

# define a mount point
ADD ./serverless_server.py serverless_server.py
ADD ./my_module.py my_module.py


# define command for this image
CMD ["python3","/serverless_server.py"]
