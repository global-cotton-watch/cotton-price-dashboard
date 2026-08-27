# 全球棉价 7 日 H5 看板

面向微信公众号菜单的移动端网页，每日采集四个市场最近 7 个交易日数据，并统一折算为人民币元/吨。

## 数据口径

| 市场 | 品种/口径 | 原始数据 | 人民币换算 |
|---|---|---|---|
| 中国 | CC Index 3128B | 中国棉花协会数据中心API，元/吨；旧站首页备用校验 | 原值 |
| 美国 | 美国棉花 2 号 | 优先 Investing.com；依次尝试官方接口、只读渲染；受限时使用 Yahoo `CT=F` 备用 | `(报价+10)/100 × 2204.6226 × USD/CNY` |
| 巴基斯坦 | Karachi Ex-Gin | PKR/37.324kg | `出厂价/37.324 × 1000 × PKR/CNY` |
| 印度 | Shankar 6 | Gujcot Rs/Candy；换算使用网站同步公布的 Rs/Quintal | `Rs/Quintal × 10 × INR/CNY` |

汇率来自 ExchangeRate-API 免费公开端点。折算价不含关税、增值税、保险及港杂费；美国“到岸参考价”严格按指定的加 10 美分规则，不代表完整进口成本。

中国市场通过中国棉花协会数据中心取得最新 7 个发布日；四个市场均以“最近 7 个有报价的交易日”展示，不用周末或节假日数据前值填充。

## 本地运行

```bash
python -m pip install -r requirements.txt
python update_prices.py
python app.py
```

访问 `http://127.0.0.1:5000`。健康检查：`GET /health`；数据接口：`GET /api/prices`。

## Docker 部署（推荐）

```bash
docker compose up -d --build
```

- Web 服务监听 `8000`。
- `updater` 启动时更新一次，之后每天北京时间 09:15 更新。
- SQLite 数据保存在 Docker volume `cotton_data` 中。
- 生产环境请在前面配置 Nginx/Caddy HTTPS，并在 `.env` 设置强随机 `UPDATE_TOKEN`。

## GitHub Pages免费试运行

仓库包含 `.github/workflows/pages.yml`：首次推送后会抓取四国最新数据、导出静态H5并部署到GitHub Pages，之后每天北京时间09:30自动更新。也可以在GitHub仓库的 **Actions** 页面手动运行。

本地预览静态导出：

```bash
python update_prices.py
python export_static.py
python -m http.server 8080 --directory site
```

访问 `http://127.0.0.1:8080`。GitHub仓库中需将 **Settings → Pages → Build and deployment → Source** 设置为 **GitHub Actions**。

### 每日公众号文章邮件

工作流每天更新网站后，会比较巴基斯坦和印度最近7个交易日的人民币参考价涨跌幅，选择绝对波动较大的市场生成标题和四国行情正文，并发送到指定邮箱。个人公众号需由管理员复制邮件内容并确认发表。

在仓库 **Settings → Secrets and variables → Actions** 中配置：

- `SMTP_USERNAME`：已开启SMTP服务的126邮箱账号
- `SMTP_AUTH_CODE`：126邮箱客户端授权码，不是邮箱登录密码
- `MAIL_TO`：接收每日文章的邮箱

授权码只保存在GitHub加密Secrets中，不能写入代码或配置文件。

## 微信公众号菜单接入

1. 将服务部署到已备案、可通过 HTTPS 访问的域名，例如 `https://cotton.example.cn/`。
2. 在微信公众平台 **设置与开发 → 公众号设置 → 功能设置 → 业务域名** 添加域名并完成校验。
3. 在 **内容与互动 → 自定义菜单** 新建“全球棉价”，类型选择“跳转网页”，填入 H5 URL 后发布。
4. 若公众号后台要求网页授权域名，本页面不读取用户身份，通常不需要 OAuth；只有后续增加会员功能时才需要配置。

## 关键配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `COTTON_DATABASE` | `data/cotton.db` | SQLite 文件位置 |
| `UPDATE_TOKEN` | 空 | 设置后，`POST /api/update` 必须带 `X-Update-Token` |
| `UPDATE_TIMEZONE` | `Asia/Shanghai` | 自动更新时区 |
| `UPDATE_HOUR` / `UPDATE_MINUTE` | `9` / `15` | 每日更新时间 |
| `JINA_API_KEY` | 空 | 可选；Investing只读渲染服务令牌，未设置或访问受限时自动切换Yahoo备用源 |
