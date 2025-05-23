import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, List

class ComplexLinear(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.Wr = nn.Parameter(torch.randn(out_features, in_features))
        self.Wi = nn.Parameter(torch.randn(out_features, in_features))
        self.br = nn.Parameter(torch.randn(out_features))
        self.bi = nn.Parameter(torch.randn(out_features))

    def forward(self, z):
        x = z.real
        y = z.imag
        real = torch.matmul(self.Wr, x) - torch.matmul(self.Wi, y) + self.br
        imag = torch.matmul(self.Wr, y) + torch.matmul(self.Wi, x) + self.bi
        return torch.complex(real, imag)
