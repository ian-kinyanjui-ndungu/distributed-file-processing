# MODULES
import socket
from socket import timeout
import argparse
import pickle
import os
import hashlib
import concurrent.futures
import time

# Pass Arguments to script via. Terminal
parser = argparse.ArgumentParser(
    description="This is the client for the multi threaded socket server!")
parser.add_argument('--ip', metavar='ip', type=str, nargs='?',
                    default=socket.gethostbyname(socket.gethostname()))
parser.add_argument('--port', metavar='port',
                    type=int, nargs='?', default=9000)
parser.add_argument('--dir', metavar='dir', type=str,
                    nargs='?', default='./downloads')
args = parser.parse_args()

# PROTOCOL
TIMEOUT_SECONDS = 10        # Timeout connection after defined seconds of inactivity
HEADER = 64                 # Size of header
# Size of a packet, multiple packets are sent if message is larger than packet size.
PACKET = 2048
FORMAT = 'utf-8'           # Message format
ADDR = (args.ip, args.port)  # Address socket server will bind to

# MESSAGES
FILE_LIST_MESSAGE = "!GET_FILE_LIST"
FILE_DOWNLOAD_MESSAGE = "!DOWNLOAD "
DISCONNECT_MESSAGE = "!DISCONNECT"

# DOWNLOAD DIRECTORY (MAKE ONE IF NOT EXISTING. CAN BE CHANGED WITH ARGUMENT)
if not os.path.exists(args.dir):
    os.makedirs(args.dir)
    print(f"{args.dir} folder created. Files will be downloaded here.")


def createSocket():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(TIMEOUT_SECONDS)
    client.connect_ex(ADDR)
    return client


def send(msg, client):
    msg = pickle.dumps(msg)
    msg = bytes(f"{len(msg):<{HEADER}}", FORMAT) + msg
    client.send(msg)


def getMessage(client):
    full_msg = b''
    new_msg = True
    while True:
        try:
            msg = client.recv(PACKET)
        except timeout:
            full_msg = "TIMEOUT"
            break

        if new_msg:
            msg_len = int(msg[:HEADER])
            new_msg = False

        full_msg += msg

        if len(full_msg)-HEADER == msg_len:
            full_msg = pickle.loads(full_msg[HEADER:])
            break

    return full_msg


def selectFilesFromList(file_list):
    print("\nSelect files to download by index number. For multiple files seperate the index number with comma:\n")
    print(f"{'Index':<8}{'File Name':<20}")
    for f in file_list:
        print(f"{file_list.index(f):<8}{f:<20}")
    li = list(map(int, input('\n').split(',')))
    dl = []

    for i in li:
        try:
            if i == file_list.index(file_list[i]):
                dl.append(file_list[i])
        except IndexError:
            print(f"Index no {i} not found!")

    print(f"Downloading {dl}\n")
    return dl


def download(file_list, mode, client):
    fail_list = []

    if mode == 0:
        for f in file_list:
            fail = downloadSerial(f, client)
            if fail:
                fail_list.append(f)
        return fail_list
    elif mode == 1:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            threads = [executor.submit(
                downloadParallel, file_list.index(f), f) for f in file_list]
            for f in concurrent.futures.as_completed(threads):
                fail = f.result()
                if fail:
                    fail_list.append(fail)
        return fail_list
    else:
        print("Invalid Input")
        return file_list


def downloadSerial(f, client):
    down_file_time = time.time()
    send(FILE_DOWNLOAD_MESSAGE+f, client)
    md5_original = getMessage(client)
    file_data = getMessage(client)
    if (md5_original == "TIMEOUT" or file_data == "TIMEOUT"):
        print(f"{f} failed to download due to time out, trying again!")
        return f
    md5_mirror = hashlib.md5(file_data).hexdigest()
    if md5_original == md5_mirror:
        file_mirror = open(os.path.join(args.dir, f), 'wb')
        file_mirror.write(file_data)
        file_mirror.close()
        print(
            f"{f} - md5: {md5_mirror} - Integrity check pass, downloaded successfully!")
        print(f"Downloaded in {time.time()-down_file_time} seconds")
    else:
        print(f"{f} - File integrity failures. trying again")
        return f


def downloadParallel(c, f):
    c = createSocket()
    down_file_time = time.time()
    send(FILE_DOWNLOAD_MESSAGE+f, c)
    md5_original = getMessage(c)
    file_data = getMessage(c)
    if (md5_original == "TIMEOUT" or file_data == "TIMEOUT"):
        print(f"{f} failed to download due to time out, trying again!")
        send(DISCONNECT_MESSAGE, c)
        c.close()
        return f
    md5_mirror = hashlib.md5(file_data).hexdigest()
    if md5_original == md5_mirror:
        file_mirror = open(os.path.join(args.dir, f), 'wb')
        file_mirror.write(file_data)
        file_mirror.close()
        print(
            f"{f} - md5: {md5_mirror} - Integrity check passed, downloaded successfully!")
        print(f"Downloaded in {time.time()-down_file_time} seconds")
        send(DISCONNECT_MESSAGE, c)
        c.close()
    else:
        print(f"{f} - File integrity failures. trying again")
        send(DISCONNECT_MESSAGE, c)
        c.close()
        return f


def run():
    client = createSocket()
    print(f"[CONNECTED] Client connected to {args.ip}")
    active = True
    try:
        while active:
            send(FILE_LIST_MESSAGE, client)
            file_list = getMessage(client)
            if file_list == "TIMEOUT":
                continue

            file_list = selectFilesFromList(file_list)

            comm = int(
                input("Enter\n0 - Serially download\n1 - Parallely download\n"))
            download_time = time.time()
            fail_list = download(file_list, comm, client)

            if fail_list:
                retry = 3
                while retry:
                    if (comm != 0 and comm != 1):
                        break
                    print(f"{fail_list} failed to download, tries left {retry}")
                    retry = retry - 1
                    fail_list = download(fail_list, comm, client)
                    if not fail_list:
                        break

            if fail_list:
                print(f"{fail_list} could not be downloaded")

            download_time = time.time()-download_time
            print(f"\nDownload Completed in: {download_time} seconds")

            send(DISCONNECT_MESSAGE, client)
            client.close()

            print("\n-\n--\n---\n[CLOSING PROGRAM]\n---\n--\n-\n")
            active = False

    except KeyboardInterrupt:
        send(DISCONNECT_MESSAGE, client)
        print("\n[KEYBOARD INTERRUPT]")


if __name__ == "__main__":
    run()
