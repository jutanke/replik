"""
A client needs to provide the following resources:
{

}
"""
import zmq
import signal
from time import time
from replik.scheduler.message import (
    get_is_alive_msg,
    get_request_uid_msg,
    get_process_msg,
)
import replik.console as console

context = zmq.Context()

socket = context.socket(zmq.REQ)
# socket.setsockopt(zmq.CONNECT_TIMEOUT, 2000)
# socket.setsockopt(zmq.LINGER, 10)

socket.connect("tcp://localhost:5555")


def send_message_with_timeout(socket, msg):
    # if the server is NOT up this send command will way forever!
    # Time-out with python instead...
    def term_handler():
        raise Exception("no server")

    failed = False
    try:
        socket.send_json(msg)
        result = message = socket.recv_json()
        signal.alarm(0)
    except Exception as exec:
        failed = True

    if failed:
        console.fail("replik server is not up")
        return True, None

    return False, result


def check_server_status():
    timeout, msg = send_message_with_timeout(socket, get_is_alive_msg())
    return not timeout


def request_uid():
    timeout, msg = send_message_with_timeout(socket, get_request_uid_msg())
    if timeout:
        console.fail("Could not request uid: Timeout!")
        exit(0)
    print(msg)
    return msg["uid"]


def request_scheduling(uid, info):
    msg = get_process_msg(uid, info)

    socket.send_json(msg)
    result = socket.recv_json()
    print("res", result)
