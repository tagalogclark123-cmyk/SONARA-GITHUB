"""SONARA model definitions (shared by SONARA_TRAIN_V6.ipynb and pi_latency_benchmark.py).

All models take a feature tensor of shape (batch, 3, 64, frames):
channel 0 = log-mel spectrogram (dB), channel 1 = delta, channel 2 = delta-delta.
All models output 2 logits: index 0 = Non-distress, index 1 = Distress.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CNN_BiLSTM(nn.Module):
    """CNN front end + bidirectional LSTM.

    pooling="final_states" (default, FIXED): concatenates the final hidden state of the
        forward direction (has read the whole sequence left to right) and of the backward
        direction (has read the whole sequence right to left).
    pooling="last_step" (LEGACY, the V5 behaviour): takes the LSTM output at the last time
        step. The backward half of that output has only seen one frame, so the model
        barely uses bidirectional context. Kept only to measure the effect of the fix.

    Attribute names (conv1, bn1, conv2, bn2, lstm, fc) match the V5 notebook, so a V5
    state_dict loads into pooling="last_step".
    """

    def __init__(self, n_mels=64, num_classes=2, cnn_channels=64, lstm_hidden=128,
                 lstm_layers=1, dropout=0.3, pooling="final_states"):
        super().__init__()
        if pooling not in ("final_states", "last_step"):
            raise ValueError("pooling must be 'final_states' or 'last_step'")
        self.pooling = pooling
        self.conv1 = nn.Conv2d(3, cnn_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(cnn_channels)
        self.conv2 = nn.Conv2d(cnn_channels, cnn_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(cnn_channels)
        self.pool = nn.MaxPool2d(kernel_size=(2, 2))
        freq_out = n_mels // 4                      # two 2x2 poolings: 64 -> 16
        # Built here (not lazily inside forward) so the model can be loaded directly on the Pi.
        self.lstm = nn.LSTM(
            input_size=cnn_channels * freq_out,     # 64 * 16 = 1024 inputs per time step
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(lstm_hidden * 2, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        b, c, fq, t = x.shape                        # (B, 64, 16, T/4)
        x = x.permute(0, 3, 1, 2).reshape(b, t, c * fq)   # sequence of T/4 steps
        out, (h_n, _) = self.lstm(x)
        if self.pooling == "final_states":
            z = torch.cat([h_n[-2], h_n[-1]], dim=1)  # final forward + final backward state
        else:
            z = out[:, -1, :]                         # legacy V5 behaviour
        return self.fc(self.dropout(z))


class CNNFrontEndOnly(nn.Module):
    """Ablation: exactly the CNN-BiLSTM front end, with global average pooling instead of the
    BiLSTM. Comparing this with CNN_BiLSTM shows what the BiLSTM adds."""

    def __init__(self, n_mels=64, num_classes=2, cnn_channels=64, dropout=0.3):
        super().__init__()
        self.conv1 = nn.Conv2d(3, cnn_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(cnn_channels)
        self.conv2 = nn.Conv2d(cnn_channels, cnn_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(cnn_channels)
        self.pool = nn.MaxPool2d(kernel_size=(2, 2))
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(cnn_channels, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        z = self.gap(x).flatten(1)
        return self.fc(self.dropout(z))


class _DSBlock(nn.Module):
    def __init__(self, ch):
        super().__init__()
        self.dw = nn.Conv2d(ch, ch, kernel_size=3, padding=1, groups=ch, bias=False)
        self.bn_dw = nn.BatchNorm2d(ch)
        self.pw = nn.Conv2d(ch, ch, kernel_size=1, bias=False)
        self.bn_pw = nn.BatchNorm2d(ch)

    def forward(self, x):
        x = F.relu(self.bn_dw(self.dw(x)))
        return F.relu(self.bn_pw(self.pw(x)))


class DSCNN(nn.Module):
    """Depthwise-separable CNN in the style of Zhang et al. (2017), "Hello Edge: Keyword
    Spotting on Microcontrollers". This is a REIMPLEMENTATION. If the team still has the
    original DS-CNN code from Table 3.1, use that instead and keep the same training loop."""

    def __init__(self, num_classes=2, channels=172, n_blocks=4, dropout=0.3):
        super().__init__()
        self.conv = nn.Conv2d(3, channels, kernel_size=(10, 4), stride=(2, 2), padding=(5, 1), bias=False)
        self.bn = nn.BatchNorm2d(channels)
        self.blocks = nn.Sequential(*[_DSBlock(channels) for _ in range(n_blocks)])
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(channels, num_classes)

    def forward(self, x):
        x = F.relu(self.bn(self.conv(x)))
        x = self.blocks(x)
        z = self.gap(x).flatten(1)
        return self.fc(self.dropout(z))


def mobilenet_v3_small(num_classes=2):
    """MobileNetV3-Small from torchvision, trained from scratch (no ImageNet weights).
    Qiao et al. (2026) evaluated MobileNetV3 on SmartEars, so this gives a published
    architecture run on OUR split."""
    from torchvision.models import mobilenet_v3_small as _mnv3
    return _mnv3(weights=None, num_classes=num_classes)


MODEL_BUILDERS = {
    "cnn_bilstm": lambda: CNN_BiLSTM(pooling="final_states"),
    "cnn_bilstm_laststep": lambda: CNN_BiLSTM(pooling="last_step"),   # legacy, for comparison only
    "cnn_frontend_only": lambda: CNNFrontEndOnly(),
    "dscnn": lambda: DSCNN(),
    "mobilenetv3_small": lambda: mobilenet_v3_small(),
}

MODEL_LABELS = {
    "cnn_bilstm": "CNN-BiLSTM (fixed pooling)",
    "cnn_bilstm_laststep": "CNN-BiLSTM (V5 last-step pooling)",
    "cnn_frontend_only": "CNN front end only (no LSTM)",
    "dscnn": "DS-CNN (binary)",
    "mobilenetv3_small": "MobileNetV3-Small",
}


def count_params(model):
    return sum(p.numel() for p in model.parameters())


def param_breakdown(model):
    """Parameters per top-level layer, for the panel's 'how were the parameters computed' question."""
    rows = []
    total = count_params(model)
    for name, module in model.named_children():
        n = sum(p.numel() for p in module.parameters())
        if n:
            rows.append((name, n, 100.0 * n / total))
    return rows, total
