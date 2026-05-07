# 移动端与 GitHub 水果分类仓库对接说明

本文档供 **手机 App 开发** 与 **本仓库（含 GitHub Actions）** 对齐使用：完成「用户授权 → 上传图片到 `incoming/` → 触发自动推理」的集成。

---

## 1. 仓库与约定

| 项 | 值 |
|----|-----|
| 仓库（示例） | `yhlkxkzs/mobileNetV3large_backend` |
| 默认分支 | `main` |
| 图片上传目录 | `incoming/`（可子目录，如 `incoming/uploads/xxx.jpg`） |
| 权重文件（仅说明，由 Action 使用） | `models/mobilenet_fruit_cls_best.pt` |
| 推理 Workflow 名称 | `Fruit classification (MobileNet V3)` |
| 工作流文件 | `.github/workflows/infer_fruit.yml` |

**触发条件**：向 **`incoming/**`** 路径产生 **push**（含通过 API 创建/更新文件导致的提交）后，会启动上述 Workflow。

---

## 2. 架构角色

- **App**：完成 GitHub OAuth、保存 `access_token`（系统密钥库）、将图片通过 **GitHub Contents API** 写入 `incoming/`。
- **GitHub**：托管仓库、执行 Actions（安装 PyTorch CPU、运行 `scripts/infer_fruit.py`）。
- **结果位置**：单次运行结束后，在 **Actions 运行页 → Artifacts** 可下载 `predictions`（内含 `predictions.json`）；**Summary** 中可能展示同一份 JSON。

> **说明**：GitHub 不提供「上传完成后立即把分类结果推回手机」的长连接。App 若要在端上展示结果，需自行实现 **轮询 GitHub Actions API**、或 **Webhook + 自有后端**、或引导用户到浏览器查看（产品化以前两种之一为准）。

---

## 2.1 自建服务器接收图片（Actions + `curl` POST）

本仓库 Workflow 在推理前可增加一步：**把本次涉及 `incoming/` 的图片用 `multipart/form-data` POST 到你的 HTTPS 接口**（由 GitHub Runner 发起，**整张文件在 `file` 字段**）。

### 你需要做的两件事

**1）在 GitHub 仓库配置 Secrets**

仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Secret 名称 | 是否必填 | 含义 |
|-------------|----------|------|
| `FRUIT_SERVER_UPLOAD_URL` | **必填**（不配则跳过转发） | 你的接收地址，例如 `https://api.example.com/v1/github/incoming` |
| `FRUIT_SERVER_UPLOAD_TOKEN` | 可选 | 若接口需要鉴权，填 Bearer token；Workflow 会加请求头 `Authorization: Bearer <token>` |

**2）你的服务器提供 POST 接口**

- **方法**：`POST`  
- **Content-Type**：`multipart/form-data`（`curl -F` 自动带 boundary）  
- **字段**：

| 字段 | 说明 |
|------|------|
| `file` | 图片二进制（整张图） |
| `path` | 仓库内相对路径，如 `incoming/uploads/xxx.jpg` |
| `commit` | 本次 GitHub commit SHA |
| `repo` | `owner/name`，如 `yhlkxkzs/mobileNetV3large_backend` |

**转发哪些文件**

- **普通 `push`**：仅 **本次提交里新增/修改** 且路径在 `incoming/` 下的图片（`jpg/jpeg/png/webp/bmp`）。  
- **`workflow_dispatch` 手动跑**：`incoming/` 下 **所有** 符合后缀的图片（便于一次性补传）。

### 服务端必须满足

- URL 使用 **HTTPS**，且 **公网可达**（GitHub 托管 Runner 的出口能访问你）。纯内网、仅校园 VPN 可访问的地址，Runner **连不上**，需改用 **自托管 Runner** 或 **公网反代**。  
- 若使用自签证书，需在服务端使用正规 CA 证书或 Runner 侧信任链能验证（否则 `curl` 会失败）。

### 与手机端的关系

手机仍按前文把图传到 GitHub `incoming/`；**推送成功后** Workflow 运行，由 Runner **再 POST 一份到你服务器**。服务器可与现有业务（入库、GPU 推理等）对接。

---

## 3. 服务端 / 产品侧需先完成（非 App 内）

1. 在 GitHub 注册 **OAuth App**（Settings → Developer settings → OAuth Apps）。  
2. 配置 **Authorization callback URL** 与 App 的 **URL Scheme / 通用链接** 一致（例如 `myapp://github-callback`）。  
3. 为换 token 二选一：  
   - **推荐**：自有 **HTTPS 后端** 保管 `client_secret`，用授权码换 `access_token`，再把 token 下发给 App（或会话态）；  
   - 或按 [GitHub 文档](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps) 使用 **PKCE** 等适用于公开客户端的方式，**禁止**把 `client_secret` 硬编码进商店安装包。  
4. 确认目标仓库为 **公开** 或 用户账号对该仓有写权限；**最小 scope** 建议：公开仓使用 `public_repo`，私有仓需更大范围（以 OAuth 文档为准）。

---

## 4. App 侧流程（与后端/运维配合）

### 4.1 用户点击「连接 GitHub」

1. App 生成随机 **`state`**（防 CSRF），可选生成 **PKCE** `code_verifier` / `code_challenge`。  
2. 使用 **系统浏览器**（或 Custom Tabs）打开授权 URL，**勿**使用无地址栏的 WebView 承载登录（安全与合规）。  

授权 URL 形态（参数名以 GitHub 最新文档为准）：

```text
https://github.com/login/oauth/authorize
  ?client_id={OAUTH_CLIENT_ID}
  &redirect_uri={URL 编码后的回调地址，与 OAuth App 配置完全一致}
  &scope=public_repo
  &state={随机 state}
  &code_challenge={可选}
  &code_challenge_method=S256
```

- 若仓库为 **私有**，`scope` 需改为文档允许的仓库写权限（通常为 `repo`，范围更大，须向用户说明）。

### 4.2 用户同意授权后

GitHub 重定向至 `redirect_uri`，携带：

```text
{scheme}://...?code={授权码}&state={与请求一致}
```

App 校验 `state` 后取出 **`code`**（一次性、短时效）。

### 4.3 用 `code` 换取 `access_token`

- 向 `https://github.com/login/oauth/access_token` 发起 **POST**（`Accept: application/json`），Body 包含 `client_id`、`code`、`redirect_uri`；若使用机密客户端则 **`client_secret` 仅在后端传递**。  
- 解析响应中的 **`access_token`**。

### 4.4 安全存储

- **Android**：`EncryptedSharedPreferences` 或基于 Keystore 的封装。  
- **iOS**：**Keychain**。  
- **禁止**明文写入 `SharedPreferences` / `UserDefaults`。  
- 提供「退出登录」并 **删除 token**。

### 4.5 上传图片（核心 API）

**创建新文件**（路径在仓库中尚不存在时）：

```http
PUT https://api.github.com/repos/yhlkxkzs/mobileNetV3large_backend/contents/incoming/{filename}
Authorization: Bearer {access_token}
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

```json
{
  "message": "fruit-classification upload from mobile",
  "content": "{文件内容的 Base64，单行无换行}",
  "branch": "main"
}
```

**约定 `filename`**：使用唯一名避免覆盖，例如：

`uploads/{yyyyMMdd_HHmmss}_{uuid}.jpg`

**Base64**：对图片二进制编码；大图建议先在端上 **压缩 JPEG** 再编码，注意 GitHub **单文件大小限制**（当前硬上限 100MB，实际宜远小于此以利移动端内存与流量）。

**更新已存在路径**：须先 **GET** 同一 `contents/...` 路径，读取响应中的 **`sha`**，再在 PUT Body 中增加 `"sha": "..."`。

官方参考：[Create or update file contents](https://docs.github.com/en/rest/repos/contents#create-or-update-a-file)

### 4.6 上传成功之后

- HTTP **201** 表示已产生一次提交；若本次提交包含 `incoming/**` 变更，**Actions 将自动排队运行**。  
- App 可提示：「已提交，识别约需数分钟，请在历史记录中查看」或对接 **Actions API** 轮询（见第 5 节）。

---

## 5.（可选）查询推理是否完成与获取结果

GitHub 提供 **Actions REST API**（需 `access_token` 且具有相应权限），例如列出 workflow runs、下载 artifacts。实现成本较高，且 artifact 下载 URL 有时效。

**简化方案**：

- 产品内嵌 **运行结果页** 的 **Web 链接**（指向该次 commit 或 Actions 列表）；或  
- 自建 **后端** 用 **repository_dispatch** / **PAT** 拉取 artifact 再推送给 App（超出本文档范围）。

若需完整 API 路径，请以 [GitHub Actions API](https://docs.github.com/en/rest/actions/workflow-runs) 为准。

---

## 6. 错误与限流（App 需处理）

| 情况 | 建议 |
|------|------|
| `401` | Token 过期或撤销，引导重新「连接 GitHub」。 |
| `403` / rate limit | 响应头含重置时间；退避重试。 |
| `409` / 缺 `sha` | 路径已存在却未带 `sha`，按 4.5 先 GET 再 PUT。 |
| 网络不可用 | 队列重试；大陆网络访问 GitHub 可能不稳定，需产品层提示或备用链路。 |

---

## 7. 联调检查清单

- [ ] OAuth 回调能稳定唤起 App，`state` 校验通过。  
- [ ] Token 仅存密钥库，日志中不打印完整 token。  
- [ ] PUT 成功后仓库 `incoming/` 下可见新文件，`main` 分支最新。  
- [ ] Actions 页面出现新运行，且 **Artifacts** 中在运行结束后有 `predictions`（当次 `incoming/` 内有可识别图片时）。  
- [ ] 未将 `client_secret` 或长期 **PAT** 打入发布包。

---

## 8. 与本仓库维护者的协作方式

| 需求 | 说明 |
|------|------|
| 修改触发路径 | 改 `.github/workflows/infer_fruit.yml` 中 `on.push.paths`。 |
| 修改推理脚本 | `scripts/infer_fruit.py`；保持 CLI 参数与 workflow 中一致。 |
| 更换模型文件 | 替换 `models/` 下权重并同步更新 `models/classes.json`（若类别有变）。 |

移动端 **无需** 随模型变更而改上传逻辑，只要仍写入 `incoming/` 且分支为 `main`（或与 workflow 约定分支一致）。

---

## 9. 文档版本

- 与仓库 `main` 分支当前结构对应；若仓库 URL 或分支名变更，请同步更新本文第 1 节与第 4.5 节中的路径。
