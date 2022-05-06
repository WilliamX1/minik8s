命令行说明：

.. code::

  version                       show minik8s version
  show pods                      display extant pods
  show services              display extant services
  start -f filepath                  start container
  start pod/service name   start stopped pod/service
  stop pod/service name             stop pod/service
  kill pod/service name             kill pod/service
  restart pod/service name       restart pod/service
  remove pod/service name         remove pod/service

yaml配置文件说明：

.. code::

  # pod
  kind: pod               # yaml配置类型
  name:                   # pod名称
  volumn:                 # 共享卷
  containers:
    - image:                  # 容器镜像名和版本 {}:{}
      command:                # 容器命令
      resource:               # 容器资源⽤量
        memory:               # 内存占用
        cpu:                  # cpu占用
      port:                   # 容器暴露的端⼝

.. code::

  # service
  kind: service           # yaml配置类型
  name:                   # service名称
  selector:               # 筛选包含的pod
  ports:                  # 暴露的端⼝
    port:                 # 对外暴露的端⼝
    targetPort:           # 对pod暴露的端⼝