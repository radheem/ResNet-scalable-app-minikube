from flask import Flask, request, jsonify
import io
from PIL import Image
from  ResNet18 import ImageClassifier  # ImagePredictor class is in a separate file called ResNet18.py

app = Flask(__name__)

# Assuming the ImagePredictor is correctly implemented
classifier = ImageClassifier()

@app.route('/', methods=['POST'])
def image_prediction():
    # Check if there is data in the request
    if not request.data:
        return jsonify({'error': 'No data in the request'}), 400

    # Try to open the image from the raw binary data
    try:
        image = Image.open(io.BytesIO(request.data))
    except Exception as e:
        return jsonify({'error': 'Invalid image data'}), 400

    # Perform the prediction
    try:
        results = classifier.predict(image, topk=2)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify(results), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
