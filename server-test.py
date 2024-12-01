import unittest
import socket
import threading
import os
import time
import sys
from client import getMessage, send
from server import *


class TestFileServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create test directory and files
        cls.test_dir = "./test_host_dir"
        if not os.path.exists(cls.test_dir):
            os.makedirs(cls.test_dir)

        # Create test files
        cls.test_files = ["test1.txt", "test2.txt", "test3.txt"]
        for file in cls.test_files:
            with open(os.path.join(cls.test_dir, file), 'w') as f:
                f.write(f"Test content for {file}")

        # Start server in separate thread
        cls.server_thread = threading.Thread(target=start)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Allow server to start

    def setUp(self):
        """Create new client connection for each test"""
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((args.ip, args.port))

    def tearDown(self):
        """Clean up after each test"""
        self.client.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Remove test files
        for file in cls.test_files:
            try:
                os.remove(os.path.join(cls.test_dir, file))
            except:
                pass
        # Remove test directory
        try:
            os.rmdir(cls.test_dir)
        except:
            pass

    def test_server_start(self):
        """Test if server starts and accepts connections"""
        self.assertTrue(self.client.getpeername())

    def test_file_list(self):
        """Test file listing functionality"""
        send(FILE_LIST_MESSAGE, self.client)
        response = getMessage(self.client)
        self.assertIsInstance(response, list)
        self.assertEqual(len(response), len(self.test_files))

    def test_file_download(self):
        """Test file download functionality"""
        test_file = self.test_files[0]
        send(FILE_DOWNLOAD_MESSAGE + test_file, self.client)
        md5_hash = getMessage(self.client)
        file_data = getMessage(self.client)
        self.assertIsNotNone(md5_hash)
        self.assertIsNotNone(file_data)

    def test_multiple_connections(self):
        """Test handling of multiple client connections"""
        clients = []
        try:
            for _ in range(5):
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((args.ip, args.port))
                clients.append(client)

            for client in clients:
                self.assertTrue(client.getpeername())
        finally:
            for client in clients:
                client.close()

    def test_invalid_request(self):
        """Test server handling of invalid requests"""
        send("INVALID_REQUEST", self.client)
        with self.assertRaises(Exception):
            getMessage(self.client)

    def test_disconnect_message(self):
        """Test proper disconnection handling"""
        send(DISCONNECT_MESSAGE, self.client)
        self.client.close()
        with self.assertRaises(Exception):
            self.client.getpeername()


def run_tests():
    unittest.main(argv=[''])


if __name__ == '__main__':
    run_tests()
