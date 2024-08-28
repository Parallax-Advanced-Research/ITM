import socket


def is_port_open(port: int) -> bool:
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect(("localhost", port))
      s.close()
      return True
   except:
      s.close()
      return False

def is_listening(host: str, port: int) -> bool:
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      ret_val = s.connect_ex((host, port))
      s.close()
      return ret_val == 0
   except:
      s.close()
      return False
