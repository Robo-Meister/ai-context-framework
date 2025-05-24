import torch
import torch.nn as nn
import torch.optim as optim


class AIInferenceEngine:
    """
    Base class for AI decision/prediction engines.
    Responsible for consuming fused context and producing AI inference results.
    Can be extended to support training and prediction.
    """

    def __init__(self, model: nn.Module = None, lr: float = 0.01):
        self.model = model
        if self.model is not None:
            self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
            self.loss_fn = nn.MSELoss()  # or any appropriate loss
        else:
            self.optimizer = None
            self.loss_fn = None

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.model:
            self.model.to(self.device)

    def infer(self, input_data: dict) -> dict:
        """
        Perform inference based on the fused context data.
        Expects input_data with a 'features' key containing a list or tensor.
        """
        self.model.eval()
        with torch.no_grad():
            features = input_data.get("features")
            if features is None:
                raise ValueError("Input data must contain 'features'")

            if not isinstance(features, torch.Tensor):
                features = torch.tensor(features, dtype=torch.float32).to(self.device)
            else:
                features = features.to(self.device)

            output = self.model(features)
            # Assuming output is a tensor of shape [1] or [batch, 1]
            prediction = output.item() if output.numel() == 1 else output.cpu().tolist()

            return {
                "prediction": prediction,
                "confidence": 1.0,  # Placeholder, can implement confidence logic
            }

    def train(self, input_data: dict, target: float) -> float:
        """
        Train the model on input data with given target value.
        Returns the loss value as float.
        """
        if self.model is None or self.optimizer is None or self.loss_fn is None:
            raise RuntimeError("Model, optimizer, or loss function not initialized")

        self.model.train()
        features = input_data.get("features")
        if features is None:
            raise ValueError("Input data must contain 'features'")

        if not isinstance(features, torch.Tensor):
            features = torch.tensor(features, dtype=torch.float32).to(self.device)
        else:
            features = features.to(self.device)

        target_tensor = torch.tensor([target], dtype=torch.float32).to(self.device)

        self.optimizer.zero_grad()
        output = self.model(features)
        loss = self.loss_fn(output, target_tensor)
        loss.backward()
        self.optimizer.step()

        return loss.item()
