#coding: utf-8

import sys, math

from twisted.python import log
from twisted.internet import reactor, defer
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.websocket import listenWS
from autobahn.wamp import exportSub, \
                          exportPub, \
                          exportRpc, \
                          WampServerFactory, \
                          WampServerProtocol
import json
from bson.objectid import ObjectId
import sys
import os
from twisted.application import internet, service
from daemon import funs


class RepeaterServerProtocol(WampServerProtocol):
    schd_name = None
    def onOpen(self):
        self.factory.register(self)
        WampServerProtocol.onOpen(self)
        
    def connectionLost(self, reason):
        WampServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)
        
    def onMessage(self, msg, binary):
        WampServerProtocol.onMessage(self, msg, binary)
        
    def onSessionOpen(self):
        self.runner_info = {}
        self.monitor_info = {}
        
        
        self.registerProcedureForRpc("clients", self.getClients)
        
        #self.registerProcedureForRpc("get_spiders", self.get_spiders)
        self.registerForRpc(self)
        
        self.registerForPubSub("spider")
        self.registerForPubSub("tasker")
        self.registerForPubSub("webadmin")
        
        self.registerForPubSub("psmonitor")
        
        log.msg("on connection sid:%s, peer:%s" % (self.session_id, self.peerstr))

    
    @exportRpc("get_spiders")
    def get_spiders(self):
        channel = "spider"
        rets = []
        if self.factory.subscriptions.has_key(channel):
            for proto in self.factory.subscriptions[channel]:
                val = {}
                val.setdefault("sid", proto.session_id)
                val.setdefault("peer", proto.peerstr)
                
                for k, v in proto.runner_info.iteritems():
                    val.setdefault(k, v)
                rets.append(val)
        return rets
    
    @exportRpc("set_info")
    def set_runner_info(self, info):
        self.runner_info = json.loads(info)
        return 'ok'
    
#     @exportRpc("init_cmd")
#     def init_cmd(self, cmd):
# #     var event = {}
# #     event.act = "start";
# #     event.kw = {
# #         spider:spider,
# #         threads:parseInt(threads),
# #         process:parseInt(process)
# #     };
#         event = {
#                  'act':'start',
#                  'kw':{'cmd':cmd}
#                  }
#         print event
#         reactor.callLater(3, self.init_cmd_cb, (event,))
#         return 'init_cmd', self.session_id
    
    
    def init_cmd_cb(self, event):
        self.factory.dispatch("spider", event)
    
    def getClients(self, channel):
        rets = []
        if self.factory.subscriptions.has_key(channel):
            for proto in self.factory.subscriptions[channel]:
                val = {}
                val.setdefault("sid", proto.session_id)
                val.setdefault("peer", proto.peerstr)
                
                rets.append(val)
        return rets
        
      
class StoreServerFactory(WampServerFactory):

    def __init__(self, url, debugWamp = False):
       WampServerFactory.__init__(self, url, debugWamp = debugWamp)
       self.clients = []

       
    def onClientSubscribed(self, proto, topicUri):
        self.bcClients(proto, topicUri, "open")
        
    def onClientUnsubscribed(self, proto, topicUri):
        self.bcClients(proto, topicUri, "close")

    def bcClients(self, proto, topicUri, action):
        '''
                                蜘蛛或任务下线。或上线。广播通知
        '''
        msg = {"msg_type":"broadcast",
               "action": action,
               "topicUri": topicUri,
               "session_id": proto.session_id
               }
        
        if topicUri == "spider":
            self.dispatch("webadmin", msg)
            
#         for k, v in self.subscriptions.iteritems():
#             self.dispatch(k, msg)
        
    def register(self, client):
        if not client in self.clients:
            print "registered client " + client.peerstr
            self.clients.append(client)
        
    def unregister(self, client):
        if client in self.clients:
            print "unregistered client " + client.peerstr
            self.clients.remove(client)


def start():
    factory = StoreServerFactory("ws://localhost:9000", debugWamp = True)
    factory.protocol = RepeaterServerProtocol
    factory.setProtocolOptions(allowHixie76 = True)
    listenWS(factory)



if __name__ == "__main__":
    log.startLogging(sys.stdout)
    reactor.callWhenRunning(start)
    reactor.run()

if __name__ == "__builtin__":
    from twisted.python.log import ILogObserver, FileLogObserver
    from twisted.python.logfile import DailyLogFile, LogFile
    reactor.callWhenRunning(start)
    application = service.Application('server_admin')
    logfile = LogFile("server_admin.log", "/var/log/", rotateLength=100000000000)
    application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
