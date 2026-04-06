#!/usr/bin/env python3
import argparse
import os
import uuid

import requests


def resolve_config(args):
    return {
        "url": args.url or os.environ.get("NOCODB_URL", "http://localhost:8020"),
        "token": args.token or os.environ.get("NOCODB_API_TOKEN", ""),
        "table_id": args.table_id or os.environ.get("NOCODB_TABLE_ID", ""),
    }


def build_headers(token):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["xc-token"] = token
    return headers


def ensure_config(config):
    if not config["token"]:
        raise SystemExit("❌ 缺少 NOCODB_API_TOKEN，请先设置环境变量或传入 --token")
    if not config["table_id"]:
        raise SystemExit("❌ 缺少 NOCODB_TABLE_ID，请先设置环境变量或传入 --table-id")


def get_workspace_tmp():
    workspace = os.environ.get("OPENCLAW_AGENT_WORKSPACE") or os.getcwd()
    tmp_dir = os.path.join(workspace, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def download_image(url, filename=None):
    try:
        tmp_dir = get_workspace_tmp()
        if not filename:
            ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
            filename = f"img_{uuid.uuid4().hex[:8]}{ext}"
        local_path = os.path.join(tmp_dir, filename)
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return local_path
    except Exception as exc:
        print(f"   ⚠️ 下载图片失败: {exc}")
        return None


def upload_image(config, image_path):
    upload_url = f"{config['url']}/api/v2/storage/upload"
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f)}
        res = requests.post(upload_url, headers={"xc-token": config["token"]}, files=files, timeout=60)
    res.raise_for_status()
    return res.json()


def build_content_payload(content=None, record_type=None, note=None):
    payload = {}
    if content is not None:
        payload["Content"] = content
        payload["Location"] = content
    if record_type:
        payload["Type"] = record_type
    if note:
        payload["Note"] = note
    return payload


def add_item(config, item_name, content=None, image_path=None, record_type=None, note=None):
    url = f"{config['url']}/api/v2/tables/{config['table_id']}/records"
    data = {"Name": item_name}
    data.update(build_content_payload(content=content, record_type=record_type, note=note))
    if image_path:
        attachment_data = upload_image(config, image_path)
        data["Photo"] = attachment_data
    response = requests.post(url, headers=build_headers(config["token"]), json=data, timeout=60)
    if response.status_code == 200:
        summary = content or ""
        if record_type:
            summary = f"[{record_type}] {summary}" if summary else f"[{record_type}]"
        print(f"✅ 已记录：{item_name} -> {summary}" + (f" (包含图片: {image_path})" if image_path else ""))
    else:
        print(f"❌ 记录失败：{response.text}")


def update_item(config, item_id, content=None, image_path=None, record_type=None, note=None):
    url = f"{config['url']}/api/v2/tables/{config['table_id']}/records"
    data = {"Id": item_id}
    if content is not None:
        data["Content"] = content
        data["Location"] = content
    if record_type:
        data["Type"] = record_type
    if note:
        data["Note"] = note
    if image_path:
        attachment_data = upload_image(config, image_path)
        data["Photo"] = attachment_data
    if len(data) == 1:
        print("❌ 未提供任何要更新的内容 (content/type/note/image)")
        return
    response = requests.patch(url, headers=build_headers(config["token"]), json=data, timeout=60)
    if response.status_code == 200:
        print(f"✅ 已更新记录 ID: {item_id}")
    else:
        print(f"❌ 更新失败：{response.text}")


def find_item(config, query):
    url = f"{config['url']}/api/v2/tables/{config['table_id']}/records"
    params = {
        "where": f"(Name,like,%{query}%)~or(Content,like,%{query}%)~or(Location,like,%{query}%)~or(Type,like,%{query}%)~or(Note,like,%{query}%)",
        "limit": 100,
    }
    response = requests.get(url, headers=build_headers(config["token"]), params=params, timeout=60)
    if response.status_code != 200:
        print(f"❌ 查询失败：{response.text}")
        return
    results = response.json().get("list", [])
    if not results:
        print(f"❌ 未找到关于 '{query}' 的记录。")
        return
    print(f"🔍 找到 {len(results)} 条相关记录：")
    for row in results:
        img_path = None
        photo_data = row.get("Photo")
        if photo_data and isinstance(photo_data, list) and photo_data:
            signed_path = photo_data[0].get("signedPath")
            if signed_path:
                img_path = f"{config['url']}/{signed_path}"
            else:
                img_path = photo_data[0].get("title")
        local_img_path = download_image(img_path) if img_path else None
        img_info = f"\n   🖼️ 图片: {local_img_path}" if local_img_path else (f"\n   🖼️ 图片(原始): {img_path}" if img_path else "")
        content_value = row.get("Content") or row.get("Location") or "N/A"
        extra = []
        if row.get("Type"):
            extra.append(f"类型: {row['Type']}")
        if row.get("Note"):
            extra.append(f"备注: {row['Note']}")
        extra_text = ("\n   " + "\n   ".join(extra)) if extra else ""
        print(
            f"- [ID:{row.get('Id')}] **{row.get('Name', 'N/A')}**\n"
            f"   📌 内容: {content_value}\n"
            f"   🕒 时间: {row.get('CreatedAt', 'N/A')}{extra_text}{img_info}"
        )


def list_items(config):
    url = f"{config['url']}/api/v2/tables/{config['table_id']}/records"
    params = {"limit": 20, "sort": "-CreatedAt"}
    response = requests.get(url, headers=build_headers(config["token"]), params=params, timeout=60)
    if response.status_code != 200:
        print(f"❌ 获取列表失败：{response.text}")
        return
    results = response.json().get("list", [])
    if not results:
        print("📭 目前没有记录任何物品。")
        return
    print("📋 最近记录的物品：")
    for row in results:
        content_value = row.get("Content") or row.get("Location") or "N/A"
        print(f"- [ID:{row.get('Id')}] {row.get('Name', 'N/A')} (📌 {content_value}) @ {row.get('CreatedAt', 'N/A')}")


def delete_item(config, item_id):
    url = f"{config['url']}/api/v2/tables/{config['table_id']}/records"
    response = requests.delete(url, headers=build_headers(config["token"]), json=[{"Id": item_id}], timeout=60)
    if response.status_code == 200:
        print(f"🗑️ 已删除记录 ID: {item_id}")
    else:
        print(f"❌ 删除失败：{response.text}")


def main():
    parser = argparse.ArgumentParser(description="Manage items and records in NocoDB.")
    parser.add_argument("--url", default=None, help="NocoDB base URL")
    parser.add_argument("--token", default=None, help="NocoDB API token")
    parser.add_argument("--table-id", default=None, help="NocoDB table ID")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_add = subparsers.add_parser("add", help="Add a new item")
    parser_add.add_argument("item", help="Name of the item")
    parser_add.add_argument("content", help="Content/feature/date description")
    parser_add.add_argument("--type", help="Record type such as location/date/feature/event", default=None)
    parser_add.add_argument("--note", help="Additional note", default=None)
    parser_add.add_argument("--image", help="Path to image file", default=None)

    parser_update = subparsers.add_parser("update", help="Update an existing item")
    parser_update.add_argument("id", type=int, help="ID of the item to update")
    parser_update.add_argument("--content", help="New content description", default=None)
    parser_update.add_argument("--type", help="New record type", default=None)
    parser_update.add_argument("--note", help="New note", default=None)
    parser_update.add_argument("--image", help="Path to new image file", default=None)

    parser_find = subparsers.add_parser("find", help="Find an item")
    parser_find.add_argument("query", help="Search query (item name or location)")

    subparsers.add_parser("list", help="List recent items")

    parser_delete = subparsers.add_parser("delete", help="Delete an item by ID")
    parser_delete.add_argument("id", type=int, help="Delete ID")

    args = parser.parse_args()
    config = resolve_config(args)
    ensure_config(config)

    if args.command == "add":
        add_item(config, args.item, args.content, args.image, args.type, args.note)
    elif args.command == "update":
        update_item(config, args.id, args.content, args.image, args.type, args.note)
    elif args.command == "find":
        find_item(config, args.query)
    elif args.command == "list":
        list_items(config)
    elif args.command == "delete":
        delete_item(config, args.id)


if __name__ == "__main__":
    main()
