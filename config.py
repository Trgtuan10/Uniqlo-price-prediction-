import argparse
import time
import torch
import datetime
import numpy as np
from torch.nn.utils import clip_grad_norm_
from tqdm import tqdm

def argument_parser():
    parser = argparse.ArgumentParser(description="attribute recognition",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--debug", action='store_false')

    parser.add_argument("--batchsize", type=int, default=8)
    parser.add_argument("--train_epoch", type=int, default=500)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--width", type=int, default=256) 
    parser.add_argument("--workers", type=int, default=4) 
    parser.add_argument("--lr_ft", type=float, default=0.01, help='learning rate of feature extractor')
    parser.add_argument("--lr_new", type=float, default=0.1, help='learning rate of classifier_base')
    parser.add_argument('--momentum', type=float, default=0.9)
    parser.add_argument('--weight_decay', type=float, default=5e-4)
    parser.add_argument("--train_split", type=str, default="train", choices=['train', 'trainval'])
    parser.add_argument("--valid_split", type=str, default="test", choices=['test', 'valid'])
    parser.add_argument('--device', default="1", type=str, help='gpu device ids for CUDA_VISIBLE_DEVICES')
    parser.add_argument("--redirector", action='store_false')
    parser.add_argument('--use_bn', action='store_false')
    parser.add_argument('--use_pretrain', default=False, type=bool)
    parser.add_argument('--pretrain_model', default="path_to_model.pt", type=str)
    parser.add_argument('--checkpoint', default="./exp", type=str)
    return parser


class AverageMeter(object):
    """ 
    Computes and stores the average and current value

    """

    def __init__(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / (self.count + 1e-20)

def batch_trainer(epoch, model, train_loader, criterion, optimizer):
    model.train()
    epoch_time = time.time()
    loss_meter = AverageMeter()
    batch_num = len(train_loader)

    lr0 = optimizer.param_groups[0]['lr']
    lr1 = optimizer.param_groups[1]['lr']
    for step, (imgs, gt_label, imgname) in enumerate(train_loader):
        
        batch_time = time.time()
        imgs, gt_label = imgs.cuda(), gt_label.cuda()
        train_predict = model(imgs)
        train_loss = criterion(train_predict, gt_label)

        train_loss.backward()
        clip_grad_norm_(model.parameters(), max_norm=10.0)
        optimizer.step()
        optimizer.zero_grad()

        loss_meter.update(train_loss)
    

        log_interval = 20
        if (step + 1) % log_interval == 0 or (step + 1) % len(train_loader) == 0:
            print(f'{time_str()}, Step {step}/{batch_num} in Ep {epoch}, {time.time() - batch_time:.2f}s ',
                  f'train_loss:{loss_meter.val:.4f}')




    print(f'Epoch {epoch}, LR0 {lr0}, LR1 {lr1}, Train_Time {time.time() - epoch_time:.2f}s, Loss: {loss_meter.avg:.4f}')

    return train_loss


# @torch.no_grad()
def valid_trainer(model, valid_loader, criterion):
    model.eval()
    loss_meter = AverageMeter()

    with torch.no_grad():
        for step, (imgs, gt_label, imgname) in enumerate(tqdm(valid_loader)):
            imgs = imgs.cuda()
            gt_label = gt_label.cuda()
            valid_predict = model(imgs)
            valid_loss = criterion(valid_predict, gt_label)
            loss_meter.update(valid_loss)

    valid_loss = loss_meter.avg
    return valid_loss,

def time_str(fmt=None):
    if fmt is None:
        fmt = '%Y-%m-%d_%H:%M:%S'

    #     time.strftime(format[, t])
    return datetime.datetime.today().strftime(fmt)