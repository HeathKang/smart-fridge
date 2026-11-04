# 鲜知：家庭冰箱 MVP

家庭内网单实例，所有访问者共享库存；不提供登录。请勿将端口映射到公网。截图会发往配置的模型服务商，应用不保存图片或记录请求内容。

## QNAP / Docker Compose

1. 确认 QNAP 支持 Docker Compose，并根据 CPU 架构构建镜像。
2. 复制 `.env.example` 为 `.env`，填写 OpenAI 兼容 API 的 Base URL（通常以 `/v1` 结尾）、密钥和支持图片输入的模型名称。
3. 在项目目录执行 `docker compose up -d --build`，通过 `http://NAS局域网IP:8100` 访问。环境变量 `FRIDGE_BIND` 可指定监听地址。
4. 数据保存在 Docker volume `fridge-data`，重建容器不会删除；升级和迁移前使用 SQLite 在线备份工具备份数据库并验证恢复。不要直接删除该 volume。

模型接口需兼容 `/chat/completions` 的图片输入和 JSON 文本输出，各供应商支持情况可能不同。模型不可用时仍可手动录入；所有识别结果及预计日期需要人工确认。日期不是食品安全保证。

## 本地运行

安装 Python 3.11+、uv 和 Node.js。运行 `uv sync`，然后在 `frontend` 目录执行 `npm ci && npm run build`，回到项目目录运行 `uv run uvicorn app.server:app --host 0.0.0.0 --port 8100`。服务会读取根目录 `.env`；未配置模型时手动录入仍可用。开发前端可在 `frontend` 目录运行 `npm run dev`，开发服务器会将 API 请求代理到 8100。
