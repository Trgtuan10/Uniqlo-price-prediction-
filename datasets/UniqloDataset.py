import os 
import pandas as pd
import torch
from torch.utils.data import Dataset
#from skimage.io import imread
import torchvision.transforms as T

class UniqloDataset(Dataset):
    def __init__(self, csv_file, root_dir, transform=None):
        self.annotations = pd.read_csv(csv_file)
        self.root_dir = root_dir
        self.transform = transform
        
    def __len__(self):
        return len(self.annotations)
    
    def __getitem__(self, index):
        img_path = self.annotations.iloc[index, 0]
        image =    imread(img_path)
        y_label = torch.tensor(int(self.annotations.iloc[index, 1]))
        
        if self.transform:
            image = self.transform(image)
            
        return (image, y_label)
    

def get_transform(args):
    height = args.height
    width = args.width
    train_transform = T.Compose([
        T.Resize((height, width)),
        T.Pad(10),
        T.RandomCrop((height, width)),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
    ])

    valid_transform = T.Compose([
        T.Resize((height, width)),
        T.ToTensor(),
    ])

    return train_transform, valid_transform

