import json
import io
import os
import zipfile
from qcloud_cos import CosConfig, CosS3Client


def main_handler(event, context):
    """
    腾讯云云函数入口 - 将 COS 文件夹打包为 ZIP
    
    事件参数 (通过函数 URL POST 请求体传入):
    {
        "bucket": "your-bucket-1234567890",
        "region": "ap-guangzhou",
        "folder": "exports/proj_xxx",
        "output_key": "exports/proj_xxx/export.zip"  # 可选
    }
    """
    try:
        # 解析参数 - 支持函数 URL 和直接调用
        if isinstance(event.get("body"), str):
            params = json.loads(event["body"])
        elif event.get("body"):
            params = event["body"]
        else:
            params = event
        
        bucket = params.get("bucket")
        region = params.get("region", "ap-guangzhou")
        folder = params.get("folder", "").rstrip("/")
        output_key = params.get("output_key") or folder + "/export.zip"
        
        if not bucket or not folder:
            return make_response(400, "Missing: bucket, folder")
        
        # 获取 COS 凭证
        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        if not secret_id or not secret_key:
            return make_response(500, "COS credentials not configured")
        
        # 初始化 COS 客户端
        client = CosS3Client(CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key
        ))
        
        # 列出文件夹下所有文件
        files = []
        marker = ""
        while True:
            resp = client.list_objects(
                Bucket=bucket,
                Prefix=folder + "/",
                Marker=marker,
                MaxKeys=1000
            )
            files.extend(resp.get("Contents", []))
            if resp.get("IsTruncated") == "false":
                break
            marker = resp.get("NextMarker") or files[-1]["Key"]
        
        # 过滤掉 zip 文件
        files = [f for f in files if not f["Key"].endswith(".zip")]
        if not files:
            return make_response(404, "No files found")
        
        # 创建 ZIP
        buf = io.BytesIO()
        count = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                key = f["Key"]
                rel = key[len(folder):].lstrip("/")
                if not rel:
                    continue
                try:
                    obj = client.get_object(Bucket=bucket, Key=key)
                    zf.writestr(rel, obj["Body"].get_raw_stream().read())
                    count += 1
                except Exception:
                    pass
        
        # 上传 ZIP
        data = buf.getvalue()
        client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=data,
            ContentType="application/zip"
        )
        
        zip_url = "https://" + bucket + ".cos." + region + ".myqcloud.com/" + output_key
        return make_response(0, "success", {
            "zip_url": zip_url,
            "file_count": count,
            "zip_size": len(data)
        })
        
    except Exception as e:
        return make_response(500, str(e))


def make_response(code, message, data=None):
    """构造响应"""
    body = {"code": code, "message": message}
    if data:
        body["data"] = data
    
    # 函数 URL 需要返回这种格式
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
