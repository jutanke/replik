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
    get_murder_msg,
    get_request_uid_msg,
    get_request_status_msg,
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

    signal.signal(signal.SIGALRM, term_handler)
    signal.alarm(5)
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


def request_uid(info):
    timeout, msg = send_message_with_timeout(socket, get_request_uid_msg(info))
    if timeout:
        console.fail("Could not request uid: Timeout!")
        exit(0)

    return msg["uid"], msg["container_name"], msg["mark"], msg["staging_mark"]


def request_to_kill_uid(uid):
    timeout, msg = send_message_with_timeout(socket, get_murder_msg(uid))
    if timeout:
        console.fail("Could not kill uid: Timeout!")
        exit(0)
    console.warning(f"uid {uid} has been listed as 'unscheduled'")


def request_server_infos():
    timeout, msg = send_message_with_timeout(socket, get_request_status_msg())
    if timeout:
        console.fail("Could not request uid: Timeout!")
        exit(0)
    return msg["status"]
