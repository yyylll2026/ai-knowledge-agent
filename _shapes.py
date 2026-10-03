"""抓取真实响应结构，确保前端字段名一字不差"""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

def call(m, p, b=None, t=None, raw=None, ctype=None):
    h = {}
    d = None
    if raw is not None:
        d = raw; h["Content-Type"] = ctype
    elif b is not None:
        d = json.dumps(b).encode(); h["Content-Type"] = "application/json"
    if t: h["Authorization"] = "Bearer " + t
    r = urllib.request.Request(BASE + p, data=d, headers=h, method=m)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def shape(o, indent=0):
    pad = "  " * indent
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:")
                shape(v, indent + 1)
            else:
                print(f"{pad}{k}: {type(v).__name__} = {repr(v)[:60]}")
    elif isinstance(o, list):
        if o:
            print(f"{pad}[列表 {len(o)} 项] 第一项:")
            shape(o[0], indent + 1)
        else:
            print(f"{pad}[空列表]")

tok = call("POST", "/api/v1/auth/login", {"username": "lisi", "password": "123456"})[1]["access_token"]

print("### POST /auth/login")
print(json.dumps(call("POST","/api/v1/auth/login",{"username":"lisi","password":"123456"})[1], ensure_ascii=False))
print()
print("### GET /auth/me")
shape(call("GET", "/api/v1/auth/me", t=tok)[1])
print()
print("### POST /knowledge/search")
shape(call("POST", "/api/v1/knowledge/search", {"query": "年假有几天？", "top_k": 2}, tok)[1])
print()
print("### POST /knowledge/chat")
shape(call("POST", "/api/v1/knowledge/chat", {"question": "年假有几天？", "top_k": 2}, tok)[1])
print()
print("### POST /knowledge/documents (上传响应)")
content = open("sample.txt","rb").read()
bd = "----b"
body = (f"--{bd}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"probe.txt\"\r\n"
        f"Content-Type: text/plain\r\n\r\n").encode() + content + f"\r\n--{bd}--\r\n".encode()
st, r = call("POST","/api/v1/knowledge/documents", raw=body, ctype=f"multipart/form-data; boundary={bd}", t=tok)
print("status =", st)
shape(r)
print()
print("### 错误响应示例 (401)")
print(json.dumps(call("GET","/api/v1/auth/me")[1], ensure_ascii=False))
print("### 错误响应示例 (400 重复注册)")
print(json.dumps(call("POST","/api/v1/auth/register",{"username":"lisi","email":"x@y.com","password":"123456"})[1], ensure_ascii=False))
