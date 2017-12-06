# Wrapper class to make dealing with logs easier

class ChannelLog():

    __channel = ""
    __logs = []
    unread = False

    def __init__(self, channel, logs):
        self.__channel = channel
        self.__logs = list(logs)

    def get_server(self): return self.__channel.server
    def get_channel(self): return self.__channel

    def get_logs(self):
        return self.__logs

    def get_name(self):
        return self.__channel.name

    def get_server_name(self):
        return self.__channel.server.name

    def append(self, message):
        self.__logs.append(message)

    def index(self, message):
        return self.__logs.index(message)

    def insert(self, i, message):
        self.__logs.insert(i, message)
