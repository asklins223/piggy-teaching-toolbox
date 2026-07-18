# COS ZIP 打包云函数

将 COS 文件夹打包为 ZIP 文件的腾讯云云函数（事件函数）。

## 部署步骤

### 1. 准备部署包

```bash
# 创建临时目录
mkdir -p /tmp/scf-zip && cd /tmp/scf-zip && rm -rf *

# 安装依赖
docker run --rm -v $(pwd):/app -w /app python:3.9 pip install 'cos-python-sdk-v5' 'urllib3<2' -t .

# 复制入口文件（从项目根目录执行）
cp scripts/scf_zip_exporter/index.py .

# 打包
zip -r scf-cos-zip.zip .
```

### 2. 创建云函数

1. 登录 [腾讯云云函数控制台](https://console.cloud.tencent.com/scf)
2. 点击「新建」→「从头开始」
3. 配置：
   - **函数类型**：`事件函数`
   - **函数名称**：`cos-zip-exporter`
   - **运行环境**：`Python 3.9`
   - **提交方法**：`本地上传 zip 包`
   - **执行方法**：`index.main_handler`
   - **内存**：`512 MB`（根据文件大小调整）
   - **执行超时**：`300 秒`
   - **地域**：与 COS 同地域

4. 上传 `scf-cos-zip.zip`

### 3. 配置环境变量

在「函数配置」→「环境变量」中添加：

| 变量名 | 值 |
|--------|-----|
| COS_SECRET_ID | 你的腾讯云 SecretId |
| COS_SECRET_KEY | 你的腾讯云 SecretKey |

### 4. 启用函数 URL

1. 进入「触发管理」
2. 点击「创建触发器」
3. 选择「函数 URL」
4. 鉴权方式选择「免鉴权」（或按需配置）
5. 创建后获取 URL：
```
https://xxxxxxxx.ap-guangzhou.tencentscf.com
```

### 5. 配置后端

在 `docker-compose.yml` 的 backend 环境变量中添加：
```yaml
- SCF_ZIP_URL=https://xxxxxxxx.ap-guangzhou.tencentscf.com
```

## 调用示例

```bash
curl -X POST https://xxxxxxxx.ap-guangzhou.tencentscf.com \
  -H "Content-Type: application/json" \
  -d '{
    "bucket": "your-bucket-1234567890",
    "region": "ap-guangzhou",
    "folder": "exports/proj_xxx"
  }'
```

## 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "zip_url": "https://xxx.cos.ap-guangzhou.myqcloud.com/exports/proj_xxx/export.zip",
    "file_count": 25,
    "zip_size": 12345678
  }
}
```

## 注意事项

1. **运行环境选择 Python 3.9**
2. **入口函数**：`index.main_handler`
3. 云函数内存限制最大 3072 MB
4. 执行超时最长 900 秒
5. 建议云函数与 COS 在同一地域
