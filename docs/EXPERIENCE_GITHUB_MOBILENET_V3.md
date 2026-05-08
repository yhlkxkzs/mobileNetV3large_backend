# 经验总结：MobileNet V3 Large 上 GitHub + 手机与数据流

本文档把本项目中 **模型托管、GitHub Actions、手机侧对接、踩坑与可选架构** 串成一条可复用的说明，便于以后换模型或换仓库名时对照。

---

## 一、把 MobileNet V3 Large 权重放到 GitHub

### 1.1 模型与体积

- 本方案使用的是 **torchvision MobileNet V3 Large** 微调后的 **`best.pt`**（约十几 MB 量级），**可直接进 Git 仓库**，无需强制 Git LFS（单文件需小于 GitHub 100MB 硬限制）。
- 仓库内约定路径示例：`models/mobilenet_fruit_cls_best.pt`，类别列表可同步放在 `models/classes.json` 或写入 checkpoint 的 `classes` 字段。

### 1.2 本地目录与推送

1. 在本地建立独立小仓库目录（仅放模型 + 推理脚本 + 文档 + workflow），与训练工程主目录**分离**，用 **复制** 权重而非移动，避免破坏原训练路径。  
2. `git init`，`git add`，`git commit`。  
3. `git remote add origin git@github.com:<用户>/<仓库>.git`（推荐 SSH，需在 GitHub 账号添加公钥）。  
4. `git push -u origin main`。  
5. 日常修改前先 **`git pull --rebase`**，再改再推，减少冲突。

### 1.3 仓库命名与文档

- 仓库名可与架构一致（例如 `mobileNetV3large_backend`），避免名称为 V2 而实际为 V3 造成误解；若暂时不一致，**README 与 checkpoint 内 `model_type` 必须写清真实架构**。

### 1.4 Cursor / Agent 提交说明

- 使用 Agent 自动提交时，提交信息里可能出现 `Co-authored-by: Cursor <cursoragent@cursor.com>`，这是联合署名，**作者仍是你**；若不希望展示，需自行改写历史或本地提交。

---

## 二、GitHub Actions：仓库内推理

### 2.1 作用

- 在 **push** 到指定路径（如 `incoming/**`）或 **手动 workflow_dispatch** 时，在 Runner 上 **checkout 仓库**，安装 **CPU 版 PyTorch**，运行 `scripts/infer_fruit.py`，读取 `models/` 下权重，对 `incoming/` 中图片做分类。

### 2.2 工作流文件位置

- **必须**放在 **`.github/workflows/*.yml`**（注意目录名以 **`.` 开头**，部分文件管理器默认隐藏，命令行用 `ls -la .github/workflows` 查看）。

### 2.3 结果在哪里

- **Job Summary**：可在步骤里把 `predictions.json` 写入 `$GITHUB_STEP_SUMMARY`。  
- **Artifacts**：用 `actions/upload-artifact` 上传 `output/predictions.json`，在 Actions 运行页 **Artifacts** 下载。

### 2.4 托管 Runner 的局限

- **延迟**：排队 + 安装依赖，通常 **分钟级**，不适合「秒回」交互。  
- **网络**：托管 Runner 在 GitHub 侧公网出口；**不能**依赖其访问 **仅校园网/内网** 的 `IP:端口`（实测会出现 **connect timeout**）。

---

## 三、手机如何把图送到 GitHub（上传）

### 3.1 推荐数据流

1. App 内 **「连接 GitHub」**：通过 **OAuth**（系统浏览器打开授权页），只申请 **最小 scope**（公开仓常见为 `public_repo`）。  
2. 用授权码换取 **`access_token`**，存入 **Android EncryptedSharedPreferences / iOS Keychain**，**禁止**明文存储，**禁止**把 PAT 或 `client_secret` 写死在安装包内。  
3. 用户选图后，将图片 **Base64**，调用 **Contents API**：  
   `PUT /repos/{owner}/{repo}/contents/incoming/{唯一文件名}`  
   提交后会产生 **push**，从而触发上述 Actions（若配置了 `paths: incoming/**`）。

### 3.2 细节约定

- **文件名**带时间戳或 UUID，避免覆盖。  
- **更新已存在路径**需先 GET 取 `sha` 再 PUT。  
- 完整字段与联调清单见 **[MOBILE_APP_INTEGRATION.md](./MOBILE_APP_INTEGRATION.md)**。

### 3.3 国内网络

- 手机与 OAuth、API 均访问 **github.com / api.github.com**；大陆网络下可能不稳定，产品需有 **失败重试** 或 **网络提示**，不能假定随时可达。

---

## 四、手机如何「拿到数据」（分类结果）

GitHub **不会**在推理完成后主动推送到手机，需任选其一：

| 方式 | 说明 |
|------|------|
| **人工** | 用户在浏览器打开仓库 **Actions** → 下载 **Artifact** 或看 **Summary**（不适合正式产品）。 |
| **App 轮询 GitHub API** | 用已保存的 token 调 **Actions REST API**，查 workflow run 状态、获取 artifact 下载链接（实现成本较高，注意权限与速率限制）。 |
| **自建后端** | Webhook 或定时任务由 **服务器拉 GitHub**，再把结果通过 **你自己的 HTTPS API** 发给 App（推荐产品化）。 |
| **端侧推理** | 模型下发到手机（TFLite 等），不依赖 GitHub 回传结果（与「用 GitHub 算」不同路线）。 |

**经验**：若只做课程/演示，「上传成功 → 提示用户稍后在 Actions 页查看」可接受；若要做成正式 App，应规划 **轮询 API** 或 **自有后端**。

---

## 五、可选：Action 内 `curl` 把原图 POST 到自建服务器

- 在 Secrets 中配置 **`FRUIT_SERVER_UPLOAD_URL`**（及可选 **`FRUIT_SERVER_UPLOAD_TOKEN`**），Workflow 在推理前可将 **本次变更的 `incoming/` 图片** `multipart/form-data` POST 到该 URL。  
- **前提**：URL 必须为 **GitHub 托管 Runner 能访问的公网 HTTPS**（或隧道 URL）。**内网 IP + 校园端口** 对托管 Runner 往往 **超时不可达**——这与「本机 curl 能通」不矛盾。  
- 替代方案：**自托管 Runner** 跑在内网；或 **服务器定时拉 GitHub**（出站），不让 GitHub 连内网。

详见 **[MOBILE_APP_INTEGRATION.md](./MOBILE_APP_INTEGRATION.md) §2.1**。

---

## 六、联调检查清单（简版）

- [ ] 权重已在 `main` 分支 `models/` 下且可被 workflow 读取。  
- [ ] `.github/workflows/` 下 YAML 无语法错误，Actions 页能出现对应 workflow。  
- [ ] `incoming/` 推送后推理 job 能跑通，Artifact 或 Summary 有 `predictions.json`。  
- [ ] 手机 OAuth + PUT 文件后，仓库网页能看到新文件且触发运行。  
- [ ] 若使用服务器转发：已用 **公网或隧道 URL** 验证 Runner 可访问（勿仅用内网 IP 判断）。  
- [ ] 无 PAT/client_secret 硬编码在 App 中。

---

## 七、相关文档索引

| 文档 | 内容 |
|------|------|
| [MOBILE_APP_INTEGRATION.md](./MOBILE_APP_INTEGRATION.md) | 移动端 OAuth、Contents API、服务器 POST、Secrets 字段说明 |
| 仓库根目录 `README.md` | 权重说明、克隆、本地推理命令 |

---

## 八、文档版本

- 与当前仓库结构及实践一致；若更换仓库名、分支或模型文件名，请同步更新第一节与移动端文档中的路径示例。
