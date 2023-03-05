from unittest import mock, TestCase

import js8call_driver


class TestClient(TestCase):

    def test_msg_recv(self):
        with mock.patch(js8call_driver.Js8CallApi.listen()) as mocked_get:
            pass

# if __name__ == '__main__':
#     main()