# 鲜知：家庭冰箱 MVP

家庭内网单实例，所有访问者共享库存；不提供登录。不要映射公网端口。图片会发往配置的模型服务商，应用不保存原图。

## 发布和部署

推送 `main` 后，GitHub Actions 测试后构建 `linux/amd64` 镜像并发布至 GHCR，标签包含完整提交 SHA；仅当该提交仍是 main 最新提交时，同步更新 `latest`。部署不会自动发生。包的可见性和访问权限由 GitHub 配置。私有镜像需要在 NAS 使用具有该包读取权限的凭据执行 `docker login ghcr.io`，不要将凭据写入仓库。QNAP 的 CPU 架构可通过 `uname -m` 确认：`x86_64` 对应 amd64。

首次安装，在 NAS 上将仓库检出到固定目录，确认 Docker Compose 可用；复制 `.env.example` 为 `.env`，填入模型地址、密钥和支持图片输入的模型名称。默认使用最新成功发布的 `latest` 镜像：

```sh
docker compose pull fridge
docker compose up -d
```

访问 `http://NAS局域网IP:8100`；`docker compose ps` 显示健康状态。数据在 Compose 命名卷 `fridge-data` 的 `/data/fridge.db`，重建容器不会删除。保持部署目录及 Compose 项目名不变，否则可能创建一个空卷；不要执行 `docker compose down -v`。NAS 旧版本如果已有数据，先确认原部署目录、Compose 项目名和卷名称，备份后在测试副本验证再迁移；不要把新建空卷当作旧数据。

### 手动更新

保持原部署目录、项目名和 `.env`，拉取并更新到 `latest`：

```sh
./scripts/update.sh
```

需要指定固定版本时，可在运行脚本前设置 `FRIDGE_IMAGE=ghcr.io/heathkang/smart-fridge:<完整提交SHA>` 并导出。`latest` 会随发布变化；更新脚本在拉取后固定本次实际镜像 ID，记录前后版本。

脚本只支持已有容器正在运行的更新：先拉取新镜像，再使用 SQLite 在线备份和完整性检查，记录旧镜像 ID 和备份路径，然后替换容器并等待健康检查。任何失败都停止并提示检查；不会自动回滚或覆盖数据库。`.deploy-state/` 保存恢复所需信息，`.deploy-lock/` 防止并发更新；中断后若锁目录残留，确认没有其他更新运行后再移除。

### 备份与恢复

默认将备份写入部署目录的 `backups/`；可设置 `FRIDGE_BACKUP_DIR` 为 NAS 本地路径。升级前备份只是第一层保护，还应定期备份到独立设备或位置并定期验证恢复。备份含家庭数据，注意访问权限。以下命令创建一份带唯一名称、不会覆盖已有文件的在线备份（默认使用 `latest`；也可以设置 `FRIDGE_IMAGE` 指定可用镜像）：

```sh
docker compose run --rm --no-deps --entrypoint python fridge -m app.backup /data/fridge.db /backups/manual-$(date -u +%Y%m%dT%H%M%S).sqlite
```

可在 QNAP 计划任务中定期运行以上命令，并设置备份清理策略；目前没有自动清理或异地复制。应定期在独立卷中验证备份可打开、完整且数据正确。

恢复会丢失备份之后的写入，先确认影响。默认使用 `latest`；若指定 `FRIDGE_IMAGE`，它必须指向包含恢复工具的镜像，备份文件必须在 `FRIDGE_BACKUP_DIR`（默认 `backups/`）中：

```sh
./scripts/restore.sh 备份文件名.sqlite --confirm-data-loss
```

脚本停止应用、验证备份，并将原数据库及其 `-wal`、`-shm` 文件归档在数据卷内，再恢复备份；执行后服务保持停止。归档也需纳入独立备份策略。恢复后，确认目标应用镜像兼容备份中的数据库版本，再手动启动：

```sh
export FRIDGE_IMAGE=兼容的镜像标签或本地镜像ID
docker compose up -d --no-build --pull never
```

更新前记录的本地旧镜像 ID 可从 `.deploy-state/previous-image-id` 查看，但不应假定旧镜像兼容已迁移的数据库；例如初次引入版本化迁移前的旧镜像并不识别版本号。检查应用日志及 `/api/health`，不要直接用旧版本覆盖新数据。恢复应先在独立测试卷中演练。
SQLite 架构通过 `PRAGMA user_version` 管理。首次启动会识别现有 MVP 结构并建立版本 1 基线；无法识别的结构或高于应用支持的版本会拒绝启动。未来每次架构变更必须添加顺序迁移并测试旧库升级。日常备份使用 SQLite 在线备份 API，不能只在数据库写入时复制单个文件。

## 本地开发

安装 Python 3.11+、uv 和 Node.js。运行 `uv sync`，然后 `npm ci --prefix frontend`、`npm run build --prefix frontend`，最后运行 `uv run uvicorn app.server:app --host 0.0.0.0 --port 8100`。服务读取根目录 `.env`；未配置模型时手动录入仍可用。前端开发可运行 `npm run dev --prefix frontend`，API 代理至 8100。运行 `uv run python -m pytest -q` 执行测试。

## 第三方图标

食材图标使用 [Twemoji](https://github.com/jdecked/twemoji)，图形版权属于 Twitter, Inc. 和其他贡献者，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可；通过 [@twemoji/svg](https://github.com/boywithkeyboard/twemoji_svg) 打包使用。操作图标使用 Ant Design Icons。
