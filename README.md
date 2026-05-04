# mobileNetV3large_backend

GitHub 侧用于存放**水果分类**推理权重（**MobileNet V3 Large**），供 Actions 或本地脚本拉取使用。

## 当前权重说明

| 文件 | 说明 |
|------|------|
| `models/mobilenet_fruit_cls_best.pt` | 水果分类 checkpoint（**MobileNet V3 Large**） |

- **类别数**：10  
- **类别顺序**（与训练时一致）：见 `models/classes.json`  
- **来源**：本地训练产物 `runs/mobilenet_v3/weights/best.pt` 复制并重命名。

## 加载示例（PyTorch）

```python
import torch
from torchvision.models import mobilenet_v3_large, MobileNet_V3_Large_Weights

ckpt = torch.load("models/mobilenet_fruit_cls_best.pt", map_location="cpu", weights_only=False)
classes = ckpt["classes"]
model = mobilenet_v3_large(weights=None)
model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, ckpt["num_classes"])
model.load_state_dict(ckpt["model_state_dict"])
model.eval()
```

## 克隆与推送

```bash
git clone git@github.com:yhlkxkzs/mobileNetV3large_backend.git
# 或: git clone https://github.com/yhlkxkzs/mobileNetV3large_backend.git
```

维护者推送更新：

```bash
git remote add origin git@github.com:yhlkxkzs/mobileNetV3large_backend.git
git push -u origin main
```

若仓库为私有，请使用已配置 SSH 密钥的 `git@github.com:...` 或带 **Personal Access Token** 的 HTTPS。
