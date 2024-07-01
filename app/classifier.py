import torch
from torchvision import transforms, models

class ImageClassifier:
    def __init__(self, model_name='resnet18', model_path=None, label_path=None):
        self.device = torch.device('cpu')  # Force to use CPU
        if model_path:
            self.model = models.resnet18()
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        else:
            self.model = torch.hub.load('pytorch/vision:v0.10.0', model_name, pretrained=True)
        self.model.eval()
        
        self.model.to(self.device)

        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        with open(label_path, "r") as f:
            self.categories = [s.strip() for s in f.readlines()]

    def preprocess_image(self, image):
        input_image = image
        input_tensor = self.preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0).to(self.device)  # Move to device here
        return input_batch

    def predict(self, image, topk=5):
        input_batch = self.preprocess_image(image)
        with torch.no_grad():
            output = self.model(input_batch)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        top_prob, top_catid = torch.topk(probabilities, topk)
        
        results = [(self.categories[top_catid[i]], top_prob[i].item()) for i in range(top_prob.size(0))]
        return results
