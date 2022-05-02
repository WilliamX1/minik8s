import pika
import ast
import requests
import json


# 回调函数
def callback(ch, method, properties, body):
    print("scheduler receive pod update!")
    config: dict = ast.literal_eval(body.decode())
    instance_name = config['instance_name']
    if not config.__contains__('node'):
        config['node'] = 'node1'
        print("instance_name = ", instance_name)
        url = "http://127.0.0.1:5050/pods/{}".format(instance_name)
        json_data = json.dumps(config)
        r = requests.post(url=url, json=json_data)


if __name__ == '__main__':
    # 创建socket链接,声明管道
    connect = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connect.channel()
    # 声明exchange名字和类型
    channel.exchange_declare(exchange="pods", exchange_type="fanout")
    # rabbit会随机分配一个名字, exclusive=True会在使用此queue的消费者断开后,自动将queue删除，result是queue的对象实例
    result = channel.queue_declare(queue="", exclusive=True)  # 参数 exclusive=True 独家唯一的
    queue_name = result.method.queue
    # 绑定pods频道
    channel.queue_bind(exchange="pods", queue=queue_name)

    # 消费信息
    channel.basic_consume(on_message_callback=callback, queue=queue_name, auto_ack=True)
    # 开始消费
    channel.start_consuming()
