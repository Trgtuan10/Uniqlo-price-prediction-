import os
import numpy as np
import torch
import time
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import ReduceLROnPlateau

from config import argument_parser, batch_trainer, valid_trainer
from datasets.UniqloDataset import UniqloDataset, get_transform
import torchvision.transforms as T
from model.resnet import resnet50, resnet101, resnext50_32x4d,resnet152,resnet18,resnet34
from model.category_model import *
from torch.utils.data import ConcatDataset
import wandb


def main(args):
    print(f'use GPU{args.device} for training')

    train_tsfm, valid_tsfm = get_transform(args)

    num_augmented_copies = 5

    augmented_datasets = []
    for _ in range(num_augmented_copies):
        augmented_datasets.append(UniqloDataset(csv_file='datasets/csv_for_category/data_cate.csv', 
                                                root_dir='datasets/images', 
                                                label_column='index',
                                                transform=train_tsfm))


    train_set = ConcatDataset(augmented_datasets)

    valid_set = UniqloDataset(csv_file='datasets/csv_for_category/data_valid.csv', 
                              root_dir='datasets/images',
                              label_column='index',
                              transform=valid_tsfm)
    
    train_loader = DataLoader(
        dataset=train_set,
        batch_size=args.batchsize,
        shuffle=True,
        num_workers=args.workers,
    )
    
    # print(f'train set: {len(train_set)} samples')

    valid_loader = DataLoader(
        dataset=valid_set,
        batch_size=args.batchsize,
        shuffle=False,
        num_workers=args.workers,
    )
    
    # print(f'valid set: {len(valid_set)} samples')
    #model
    backbone = resnet18()
    model = Uniql_category_model(backbone)

    device = torch.device("cuda:" + args.device if torch.cuda.is_available() else "cpu")
    model.to(device)
    if args.use_pretrain==True:
        model_path = args.pretrain_model  # luu dia chi cua model
        checkpoint = torch.load(model_path, map_location=torch.device(device))
        model.load_state_dict(checkpoint['state_dict'])
    
    
    # save checkpoint
    exp_dir = args.checkpoint
    #name with date
    last_checkpoint_filename = f'cate_model_lr_{args.lr_ft}_{args.lr_new}.pt'
    last_checkpoint_path = os.path.join(exp_dir, last_checkpoint_filename)

    criterion = nn.CrossEntropyLoss()
    param_groups = [{'params': model.finetune_params(), 'lr': args.lr_ft},
                    {'params': model.fresh_params(), 'lr': args.lr_new}]
    optimizer = torch.optim.Adam(param_groups, weight_decay=args.weight_decay)
    lr_scheduler = ReduceLROnPlateau(optimizer, factor=0.1, patience=4)

    # Initialize Weights & Biases
    if args.log:
        wandb.init(project="Uniqlo price prediction", name = f'Uniqlo_category_lr_{args.lr_ft}_{args.lr_new}')

    #training
    for i in range(args.train_epoch):
        print(f'start epoch :  {i+1}')
        train = batch_trainer(
            epoch=i,
            model=model,
            train_loader=train_loader,
            criterion=criterion,
            optimizer=optimizer,
            device=device,
        )

        valid = valid_trainer(
            model=model,
            valid_loader=valid_loader,
            criterion=criterion,
            device=device,
        )

        lr_scheduler.step(metrics=valid[0])
        
        #log
        if args.log:
            wandb.log({
            "Train Category Loss": train[0], 
            "Train Category Accuracy": train[1],
            "Validation Category Loss": valid[0], 
            "Validation Category Accuracy": valid[1],
            })

        print("-----------------------------------------------------------------------------------------------------------")

    # save checkpoint
    save_checkpoint(model, last_checkpoint_path)
    print("save checkpoint succesfully.")


def save_checkpoint(model, filepath):
    checkpoint = {
        'state_dict': model.state_dict(),
    }
    if not os.path.exists(filepath):
        torch.save(checkpoint, filepath) 

if __name__ == '__main__':
    parser = argument_parser()
    args = parser.parse_args()
    main(args)