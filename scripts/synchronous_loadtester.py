import requests
import os

def upload_image(api_url,image_path):
        with open(image_path, 'rb') as img:
            files = {'image': img}
            
            response = requests.post(api_url, files=files)
            return response

def post_images(api_url, image_path, batch_size):
    for i in range(0, batch_size):
        response = upload_image(api_url,image_path)
        if response.status_code == 200:
            print(f"Image {os.path.basename(image_path)} uploaded successfully.")
        else:
            print(f"Image {os.path.basename(image_path)} failed with status code: {response.status_code}")
            print("Response:", response.text)
        
if __name__ == "__main__":
    api_url = "http://127.0.0.1:5000/predict"  
    image_folder = "./data/sampleImages/n01440764_tench.JPEG"
    batch_size = 200 
    post_images(api_url, image_folder,batch_size)
