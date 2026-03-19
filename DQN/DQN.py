import torch
import torch.nn as nn
import torch.nn.functional as F

class SpatialAttention(nn.Module):
    def __init__ (self, kernel_size = 7):
        assert kernel_size % 2 == 1
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        avg_out = x.mean(dim=1, keepdim=True)
        max_out, _ = x.max(dim=1, keepdim=True)
        attention = torch.cat([avg_out, max_out], dim=1)
        attention = self.sigmoid(self.conv(attention))
        return x * attention
    
class ResBlock(nn.Module):
    def __init__ (self, channels, sa_kernel_size = 3, dropout_rate = 0.1):
        super(ResBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, sa_kernel_size, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, sa_kernel_size, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.spatial_attention = SpatialAttention()
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout2d(dropout_rate)
        
    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.dropout(out)
        out = out + residual
        out = self.spatial_attention(out)
        return self.relu(out)

class QValueHead(nn.Module):
    def __init__ (self, in_channels, num_actions = 4672):
        super(QValueHead, self).__init__()
        self.conv = nn.Conv2d(in_channels, 2, kernel_size=1)
        self.bn = nn.BatchNorm2d(2)
        self.relu = nn.ReLU(inplace=True)
        self.fc = nn.Linear(2 * 8 * 8, num_actions)
        self.pool = nn.AdaptiveAvgPool2d((8, 8))
        
    def forward(self, x):
        x = self.relu(self.bn(self.conv(x)))
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)

class DQN(nn.Module):
    def __init__ (self,
                in_channels = 119,
                num_filters =  258,
                num_blocks = 20,
                num_actions = 4672,
                sa_kernel_size = 3
                ):
        super(DQN, self).__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, num_filters, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(num_filters),
            nn.ReLU(inplace=True)
        )
        self.blocks = nn.Sequential(
            *[ResBlock(num_filters, sa_kernel_size) for _ in range(num_blocks)]
        )
        self.fc = QValueHead(num_filters, num_actions)
        self._init_weights()
        
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
        
    def forward(self, x, legal_moves_mask=None):
        x = self.stem(x)
        x = self.blocks(x)
        
        q_values = self.fc(x)
        if legal_moves_mask is not None:
            q_values = q_values.masked_fill(~legal_moves_mask, float('-inf'))
                    
        return q_values
    