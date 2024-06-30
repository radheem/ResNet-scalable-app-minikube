import torch
from torchvision import models

def save_model(model_name='resnet18', model_path='models/resnet18.pth'):
    model = models.resnet18(pretrained=True)
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    save_model()
