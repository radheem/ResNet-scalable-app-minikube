import sys
sys.path.append('./submodules/load_tester')

import os
import json
from typing import Tuple, List
from barazmoon import BarAzmoon
import requests
import os


def load_workload(file_path: str) -> List[str]:
    with open(file_path, 'r') as file:
        content = file.read().strip()
        integers = [int(x) for x in content.split()]
    return integers

class MyLoadTester(BarAzmoon):
    request_count = 0
    successful_count = 0
    failure_count = 0
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
            self.request_count += 1
            response_json = response.json() if isinstance(response, requests.Response) else response            
            return True  
        except json.JSONDecodeError:
            print(f"Failed to decode response for data id: {sent_data_id}")
            return False 


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))
    workload = load_workload(dir_path+'/../data/workload.txt')
    image_folder = dir_path+'/../data/sampleImages'
    endpoint = 'http://127.0.0.1/predict'

    tester = MyLoadTester(image_folder, workload, endpoint)
    tester.start()
