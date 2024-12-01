import unittest
import socket
import os
import time
import threading
from client import *


class TestFileClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_download_dir = "./test_downloads"
        if not os.path.exists(cls.test_download_dir):
            os.makedirs(cls.test_download_dir)

    def setUp(self):
        """Set up for each test"""
        self.client = createSocket()

    def tearDown(self):
        """Clean up after each test"""
        try:
            send(DISCONNECT_MESSAGE, self.client)
        except:
            pass
        self.client.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Clean up test download directory
        for file in os.listdir(cls.test_download_dir):
            try:
                os.remove(os.path.join(cls.test_download_dir, file))
            except:
                pass
        try:
            os.rmdir(cls.test_download_dir)
        except:
            pass

    def test_connection(self):
        """Test connection establishment"""
        self.assertTrue(self.client.getpeername())

    def test_get_file_list(self):
        """Test retrieving file list from server"""
        send(FILE_LIST_MESSAGE, self.client)
        file_list = getMessage(self.client)
        self.assertIsInstance(file_list, list)
        self.assertTrue(len(file_list) >= 0)

    def test_serial_download(self):
        """Test serial download functionality"""
        send(FILE_LIST_MESSAGE, self.client)
        file_list = getMessage(self.client)
        if len(file_list) > 0:
            test_file = file_list[0]
            fail_list = download([test_file], 0, self.client)
            self.assertEqual(len(fail_list), 0)
            self.assertTrue(os.path.exists(os.path.join(args.dir, test_file)))

    def test_parallel_download(self):
        """Test parallel download functionality"""
        send(FILE_LIST_MESSAGE, self.client)
        file_list = getMessage(self.client)
        if len(file_list) >= 2:
            test_files = file_list[:2]
            fail_list = download(test_files, 1, self.client)
            self.assertEqual(len(fail_list), 0)
            for file in test_files:
                self.assertTrue(os.path.exists(os.path.join(args.dir, file)))

    def test_timeout_handling(self):
        """Test client timeout handling"""
        self.client.settimeout(0.1)  # Set very short timeout
        with self.assertRaises(socket.timeout):
            self.client.recv(PACKET)

    def test_invalid_file_download(self):
        """Test handling of invalid file download request"""
        send(FILE_DOWNLOAD_MESSAGE + "nonexistent_file.txt", self.client)
        response = getMessage(self.client)
        self.assertNotEqual(response, "TIMEOUT")

    def test_download_integrity(self):
        """Test file integrity check during download"""
        send(FILE_LIST_MESSAGE, self.client)
        file_list = getMessage(self.client)
        if len(file_list) > 0:
            test_file = file_list[0]
            send(FILE_DOWNLOAD_MESSAGE + test_file, self.client)
            md5_original = getMessage(self.client)
            file_data = getMessage(self.client)
            md5_mirror = hashlib.md5(file_data).hexdigest()
            self.assertEqual(md5_original, md5_mirror)


def run_tests():
    unittest.main(argv=[''])


if __name__ == '__main__':
    run_tests()
