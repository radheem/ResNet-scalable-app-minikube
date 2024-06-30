import sys
sys.path.append('./submodules/load_tester')

import os
import json
from typing import Tuple, List
from barazmoon import BarAzmoon
import requests
import os


class MyLoadTester(BarAzmoon):
    def __init__(self, image_folder: str, workload: List[int], endpoint: str):
        super().__init__(workload=workload, endpoint=endpoint, http_method="post")
        self.image_folder = image_folder
        self.image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.JPEG'))]
        self.index = 0

    def get_request_data(self) -> Tuple[str, bytes]:
        if not self.image_files:
            raise ValueError("No image files found in the specified folder.")

        file_name = self.image_files[self.index]
        file_path = os.path.join(self.image_folder, file_name)
        with open(file_path, 'rb') as f:
            file_data = f.read()

        self.index += 1
        if self.index >= len(self.image_files):
            self.index = 0

        return file_name, file_data

    def process_response(self, sent_data_id: str, response: requests.Response):
        try:
            response_json = response.json() if isinstance(response, requests.Response) else response
            print(f"Sent data id: {sent_data_id}")
            print(f"Response: {response_json}")
            return True  # Indicate success
        except json.JSONDecodeError:
            print(f"Failed to decode response for data id: {sent_data_id}")
            return False  # Indicate failure


if __name__ == "__main__":
    first_250_secs = [20] * 250
    last_100_secs = [20] * 100
    set1 = [1] * 400
    set2 = [60] * 25
    set3 = [70] * 25
    set4 = [75] * 150
    set5 = [40] * 50
    workload = [*set1]  
    image_folder = './data/sampleImages'
    endpoint = 'http://127.0.0.1:80/predict'

    tester = MyLoadTester(image_folder, workload, endpoint)
    tester.start()
