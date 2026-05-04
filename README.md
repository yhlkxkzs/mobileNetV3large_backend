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
in_features = model.classifier[-1].in_features
model.classifier[-1] = torch.nn.Linear(in_features, ckpt["num_classes"])
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

## 用 GitHub Actions 识别图片（上传 → 自动推理）

思路：**把待测图片放进仓库的 `incoming/` 并推送到 GitHub**，或 **手动跑一次 workflow**；Action 里会加载 `models/mobilenet_fruit_cls_best.pt` 并写出 `output/predictions.json`，可在运行日志的 **Summary** 里查看，或在 **Artifacts** 里下载 `predictions.json`。

### 步骤

1. 将图片放到 **`incoming/`**（支持子目录；格式：jpg / png / webp 等常见后缀）。
2. **提交并推送** 到 `main`（或包含 `incoming/` 变更的分支）：
   ```bash
   git add incoming/your_photo.jpg
   git commit -m "Add image for inference"
   git push
   ```
3. 打开 GitHub 仓库页 → **Actions** → 进入最新一次 **Fruit classification (MobileNet V3)** 运行记录：
   - 页面底部 **Artifacts** 可下载 **`predictions`**（内含 JSON）；
   - **Summary** 中会嵌入推理 JSON（若有结果文件）。

也可在 **Actions** 里选中该 workflow → **Run workflow** 手动触发（仍会扫描当前分支上的 `incoming/` 内图片）。

### 本地推理（与训练相同预处理）

```bash
pip install torch torchvision pillow
python scripts/infer_fruit.py incoming/apple.jpg
# 或扫描整个 incoming/：
python scripts/infer_fruit.py
```

默认输出：`output/predictions.json`（已加入 `.gitignore`，一般不会误提交）。
