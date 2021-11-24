from twisted.spread import pb
from twisted.internet import reactor

from util import timer


class ClusterPBServerFactory(pb.PBServerFactory):
    """集群rcp服务端"""
    def clientConnectionMade(self, protocol):
        """当有一个连接连接时"""
        pass


class ClusterPBClientFactory(pb.PBClientFactory):
    """集群rcp客户端"""
    # 重连的时间间隔
    reconnect_interval = 2

    def reconnect(self, connector):
        print(f"{self} reconnecting...")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        """客户端连接服务器失败后，尝试重新连接"""
        # 延迟重连
        timer.add_later_task(self.reconnect_interval, self.reconnect, connector)

    def clientConnectionLost(self, connector, reason, reconnecting=1):
        super(ClusterPBClientFactory, self).clientConnectionLost(connector, reason, reconnecting)
        # 延迟重连
        timer.add_later_task(self.reconnect_interval, self.reconnect, connector)


class Root(pb.Root):
    def __init__(self):
        # cluster.service.Service
        self._service = None

    def start(self, port):
        reactor.listenTCP(port, ClusterPBServerFactory(self))

    def remote_ping(self):
        return "pong"

    def set_service(self, service):
        """设置消息处理"""
        self._service = service

    def remote_handle(self, nodeid, key, *args, **kwargs):
        """调用远程的服务"""
        return self._service.call_handler(key, *args, **kwargs)


class Remote:
    def __init__(self, host, port, name):
        self._host = host
        self._port = port
        self._name = name
        self._factory = None

    def connect_remote(self):
        self._factory = ClusterPBClientFactory()
        # 连接远端的时候必须增加延时操作
        timer.add_later_task(1, reactor.connectTCP, self._host, self._port, self._factory)

    def call_remote_handler(self, nodeid, name, *args, **kwargs):
        """调用远程的处理函数"""
        root = self._factory.getRootObject()
        return root.addCallback(lambda d: d.callRemote("handle", nodeid, name, *args, **kwargs))