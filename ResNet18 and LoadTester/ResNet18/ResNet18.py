import torch
from torchvision import transforms

class ImageClassifier:
    def __init__(self, model_name='resnet18', pretrained=True, device=None):
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = torch.hub.load('pytorch/vision:v0.10.0', model_name, pretrained=pretrained)
        self.model.eval()
        self.model.to(self.device)

        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        with open("./imagenet_classes.txt", "r") as f:
            self.categories = [s.strip() for s in f.readlines()]

    def preprocess_image(self, image):
        input_image = image
        input_tensor = self.preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0)  # create a mini-batch as expected by the model
        return input_batch

    def predict(self, image, topk=5):
        input_batch = self.preprocess_image(image)
        input_batch = input_batch.to(self.device)

        with torch.no_grad():
            output = self.model(input_batch)

        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        top_prob, top_catid = torch.topk(probabilities, topk)
        
        results = [(self.categories[top_catid[i]], top_prob[i].item()) for i in range(top_prob.size(0))]
        return results
