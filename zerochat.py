import socket
import sys
import threading
import datetime
import select
import time

seperator = ","

print("Welcome to ZeroChat!")

online_users = {}

zerochat_username = input("Choose a username: ")

print("ZEROCHAT_USERNAME", zerochat_username)


def get_host_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    host_ip_address = s.getsockname()[0]
    s.close()
    return host_ip_address


host_ip_address = get_host_ip_address()


def ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except socket.error:
        return False
    return True


if not ipv4_address(host_ip_address):
    print("Host ip address [{host_ip_address}] is not an ipv4 address, ZeroChat is terminated!")
    sys.exit()

host_ipv4_address = host_ip_address

print("HOST_IPV4_ADDRESS", host_ipv4_address)

zerochat_port = 12345

def response(target_ipv4_address):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((target_ipv4_address, int(zerochat_port)))
            package = f"[{zerochat_username}, {host_ipv4_address}, response]"
            s.sendall(package.encode("ascii"))
        except socket.timeout:
            pass
        except socket.error:
            pass

def parse(package):
    #print("parse", package)
    first_seperator_index = package.find(seperator)

    name = package[1: first_seperator_index]

    second_seperator_index = package.find(seperator, first_seperator_index + 1)

    ipv4_address = package[first_seperator_index + 2: second_seperator_index]

    third_seperator_index = package.find(seperator, second_seperator_index + 2)

    if third_seperator_index == -1:
        command = package[second_seperator_index + 2: -1]

        if command == "announce":
            if name != zerochat_username:
                if name not in online_users:
                    online_users[name] = ipv4_address
                    print(f"{name} is online!")
                threading.Thread(target=response, args=(ipv4_address,)).start()
        elif command == "response":
            if name not in online_users:
                online_users[name] = ipv4_address
                print(f"{name} is online!")
    else:
        command = package[second_seperator_index + 2: third_seperator_index]
        if command == "message":
            message = package[third_seperator_index + 2: -1]
            print(f"{name}:{message}")


def handle(conn, addr):
    package = ""
    while True:
        data = conn.recv(1024).decode("ascii")
        if not data:
            break
        package += data

    if package:
        parse(package)
    conn.close()

def listen():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host_ipv4_address, zerochat_port))
        s.listen(10)
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle, args=(conn, addr)).start()


def listenUDP():
    #print("listenUDP")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.bind((host_ipv4_address, zerochat_port))
        s.setblocking(0)
        while True:
            result = select.select([s], [], [])
            data = result[0][0].recv(1024)
            package = data.decode("ascii")
            #print("listenUDP-received", package)
            threading.Thread(target=parse, args=(package,)).start()


threading.Thread(target=listen).start()
threading.Thread(target=listenUDP).start()


def announceUDP():
    #print("announceUDP")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host_ipv4_address, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        package = f"[{zerochat_username}, {host_ipv4_address}, announce]"
        for _ in range(3):
            s.sendto(package.encode("ascii"), ('<broadcast>', zerochat_port))
            #print("announceUDP-send", package)


threading.Thread(target=announceUDP()).start()

last_announcement_time = datetime.datetime.now()

print("announce/online/message/exit")

while True:
    command = input().strip()

    if command == "exit":
        sys.exit()
    elif command == "announce":
        if datetime.datetime.now() - last_announcement_time > datetime.timedelta(minutes=1):
            last_announcement_time = datetime.datetime.now()
            threading.Thread(target=announceUDP()).start()
        else:
            print("Rate Limited!")
    elif command == "online":
        print(online_users)
    elif command.startswith("message"):
        first_seperator_index = command.find(" ")
        second_seperator_index = command.find(" ", first_seperator_index + 1)
        target_username = command[first_seperator_index + 1: second_seperator_index]
        message = command[second_seperator_index + 1:]

        if target_username in online_users:
            target_ipv4_address = online_users[target_username]
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((target_ipv4_address, zerochat_port))
                package = f"[{zerochat_username}, {host_ipv4_address}, message, {message}]"
                s.sendall(package.encode("ascii"))
        else:
            print("No such user exists!")