import torch.nn as nn
import torch

from core.learning.complex_linear import ComplexLinear


class ComplexNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.fc1 = ComplexLinear(input_size, hidden_size)
        self.fc2 = ComplexLinear(hidden_size, output_size)

    def forward(self, z):
        z = self.fc1(z)
        mag = torch.abs(z)
        mag = torch.relu(mag)
        z = torch.complex(mag, torch.zeros_like(mag))
        z = self.fc2(z)
        return z


# Example input
# x = torch.tensor([0.5, 1.0, -0.2])
# y = torch.tensor([0.1, -0.3, 0.7])
# z = torch.complex(x, y)
#
# model = ComplexNet(input_size=3, hidden_size=5, output_size=2)
# output = model(z)
# print("Output:", output)

# import torch
#
# # Example main data (real part)
# x = torch.tensor([0.5, 1.0, -0.2])
#
# # Example context (imaginary part)
# y = torch.tensor([0.1, -0.3, 0.7])
#
# # Combine into complex tensor (PyTorch supports complex numbers)
# z = torch.complex(x, y)
