import socket


def is_port_open(port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect(("localhost", port))
      s.close()
      return True
   except:
      s.close()
      return False