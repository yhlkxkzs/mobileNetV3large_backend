#!/usr/bin/env python3
"""对单张或多张图片做水果分类推理（与训练时一致的预处理）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if _SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, _SCRIPTS.as_posix())
from fruit_display_zh import friendly_zh  # noqa: E402

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import mobilenet_v3_large, MobileNet_V3_Large_Weights

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = REPO_ROOT / "models" / "mobilenet_fruit_cls_best.pt"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".ppm", ".tif", ".tiff"}


def load_model(weights_path: Path, device: torch.device):
    ckpt = torch.load(weights_path, map_location="cpu", weights_only=False)
    class_names = ckpt.get("classes")
    num_classes = ckpt.get("num_classes")
    if class_names is None:
        class_names = [str(i) for i in range(num_classes or 0)]
    if num_classes is None:
        num_classes = len(class_names)

    weights = MobileNet_V3_Large_Weights.IMAGENET1K_V2
    model = mobilenet_v3_large(weights=weights)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.eval()
    return model.to(device), class_names


def build_transform():
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )


def predict_one(model, transform, device, image_path: Path, class_names: list[str]) -> dict:
    img = Image.open(image_path).convert("RGB")
    x = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]
    idx = int(probs.argmax().item())
    top5 = probs.topk(min(5, len(class_names)))
    labels = [class_names[i] for i in top5.indices.tolist()]
    scores = [float(v) for v in top5.values.tolist()]
    raw_main = class_names[idx]
    return {
        "image": str(image_path.as_posix()),
        "predicted_class": friendly_zh(raw_main),
        "raw_class": raw_main,
        "confidence": float(probs[idx].item()),
        "top5": [
            {"class": friendly_zh(labels[i]), "raw_class": labels[i], "score": scores[i]}
            for i in range(len(labels))
        ],
    }


def collect_images(incoming: Path) -> list[Path]:
    if not incoming.exists():
        return []
    out: list[Path] = []
    for p in sorted(incoming.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXT:
            out.append(p)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="MobileNet V3 Large 水果分类推理")
    p.add_argument(
        "--weights",
        type=Path,
        default=DEFAULT_WEIGHTS,
        help="checkpoint 路径",
    )
    p.add_argument(
        "--incoming",
        type=Path,
        default=REPO_ROOT / "incoming",
        help="待识别图片目录（递归扫描）",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "output" / "predictions.json",
        help="预测结果 JSON 路径",
    )
    p.add_argument(
        "images",
        nargs="*",
        type=Path,
        help="可选：直接指定若干图片路径；留空则扫描 --incoming",
    )
    args = p.parse_args()

    weights = args.weights if args.weights.is_absolute() else REPO_ROOT / args.weights
    if not weights.exists():
        print(f"权重不存在: {weights}", file=sys.stderr)
        return 1

    if args.images:
        paths = []
        for x in args.images:
            xp = x if x.is_absolute() else REPO_ROOT / x
            if not xp.exists():
                print(f"图片不存在: {xp}", file=sys.stderr)
                return 1
            paths.append(xp)
    else:
        paths = collect_images(args.incoming)

    if not paths:
        print("未找到图片：请将图片放入 incoming/ 或通过参数传入路径。", file=sys.stderr)
        return 0

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, class_names = load_model(weights, device)
    transform = build_transform()
    results = [predict_one(model, transform, device, im, class_names) for im in paths]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"weights": str(weights), "count": len(results), "predictions": results}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
