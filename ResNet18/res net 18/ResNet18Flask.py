from flask import Flask, request, jsonify
import os
import io
from werkzeug.utils import secure_filename
from PIL import Image
from  ResNet18 import ImageClassifier  # Assuming the ImagePredictor class is in a separate file called image_predictor.py

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'

# Assuming the ImagePredictor is correctly implemented
classifier = ImageClassifier()

@app.route('/image_prediction', methods=['POST'])
def image_prediction():
    # Check if there is data in the request
    if not request.data:
        return jsonify({'error': 'No data in the request'}), 400

    # Try to open the image from the raw binary data
    try:
        image = Image.open(io.BytesIO(request.data))
    except Exception as e:
        return jsonify({'error': 'Invalid image data'}), 400

    # # Optionally, save the image to a temporary file
    # filename = secure_filename("temp_image.jpg")
    # filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    # image.save(filepath)

    # Ensure the image is a JPG
    # if not filename.lower().endswith('.jpg'):
        # os.remove(filepath)  # Clean up the saved file
        # return jsonify({'error': 'Only JPG files are allowed'}), 400

    # Perform the prediction
    try:
        results = classifier.predict(image, topk=2)
    except Exception as e:
        # os.remove(filepath)  # Clean up the saved file
        return jsonify({'error': str(e)}), 500

    # os.remove(filepath)  # Clean up the saved file after prediction

    return jsonify(results), 200

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
