FROM ubuntu
MAINTAINER xxx <user@example.org>

# update ubuntu repository
RUN DEBIAN_FRONTEND=noninteractive apt-get -y update

# install ubuntu packages
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install python3 python3-pip

RUN pip install flask -i https://pypi.douban.com/simple

# define a mount point
ADD serverless_server.py serverless_server.py
ADD my_module.py my_module.py
ADD requirements.txt requirements.txt

# install python requirements


RUN pip install -r requirements.txt -i https://pypi.douban.com/simple



EXPOSE 5052

# define command for this image
CMD ["python3","/serverless_server.py"]