โครงสร้างเริ่มต้นเอาง่าย ๆ แบบนี้:

```text
oj-project/
├── main.py
└── problems/
```

ใน `main.py` ใส่:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "OJ server is running"}
```

```
python3 -m venv venv
source venv/bin/activate
```


จากนั้นติดตั้ง:

```bash
pip install fastapi uvicorn
```

แล้วรัน:

```bash
uvicorn main:app --reload
```

ถ้าสำเร็จ terminal จะขึ้นประมาณ:

```text
Uvicorn running on http://127.0.0.1:8000
```

เปิดใน browser:

```text
http://127.0.0.1:8000/
```

ควรเห็น:

```json
{
    "message": "OJ server is running"
}
```

อีกหน้าที่สำคัญมากคือ:

```text
http://127.0.0.1:8000/docs
```

FastAPI จะสร้างหน้า **Swagger UI** ให้เอง เราจะใช้หน้านี้ทดสอบ API ตลอดการบ้าน ไม่ต้องเขียน frontend ก่อน

ตรงโค้ดนี้:

```python
app = FastAPI()
```

คือสร้าง FastAPI application object คล้ายกับตอน Django มีตัว project/server แต่ FastAPI เบากว่ามาก

ส่วน:

```python
@app.get("/")
```

หมายความว่า

```text
เมื่อมี HTTP GET request มาที่ /
→ ให้เรียกฟังก์ชัน root()
```

และ:

```python
async def root():
```

เราใช้ `async def` เพราะการบ้านนี้กำหนดให้ API เป็น asynchronous

---

## ต่อเลย ขั้นที่ 3: ให้ Python อ่าน `P1001.json` ได้ก่อน

เปิด `main.py` แล้วแก้เป็นแบบนี้:

```python
from fastapi import FastAPI
import json

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "OJ server is running"}


@app.get("/test-problem")
async def test_problem():
    with open("problems/P1001.json", "r", encoding="utf-8") as f:
        problem = json.load(f)

    return problem
```

เซฟไฟล์ แล้วถ้าคุณรันด้วย:

```bash
uvicorn main:app --reload
```

อยู่แล้ว มันจะ reload ให้อัตโนมัติ

จากนั้นเปิด:

```text
http://127.0.0.1:8000/test-problem
```

ควรเห็น JSON ของ `P1001` ทั้งก้อนบนหน้าเว็บ

หรือเปิด:

```text
http://127.0.0.1:8000/docs
```

แล้วจะเห็น endpoint ใหม่ชื่อ:

```text
GET /test-problem
```

ตรงนี้สิ่งที่เกิดขึ้นคือ:

```python
with open("problems/P1001.json", "r", encoding="utf-8") as f:
```

เปิดไฟล์ JSON แบบอ่านอย่างเดียว

แล้ว:

```python
problem = json.load(f)
```

แปลง JSON ในไฟล์เป็น Python `dict`

เช่นหลังอ่านเสร็จ:

```python
problem["id"]
```

จะได้:

```text
P1001
```

และ:

```python
problem["title"]
```

จะได้:

```text
A+B Problem
```

ตอนนี้ endpoint `/test-problem` เป็นแค่ตัวทดลอง ยังไม่ใช่ API ตามการบ้านจริง

ถ้าอันนี้เปิดได้ปกติ ขั้นถัดไปเราจะทำ API จริงตัวแรก:

```text
GET /api/problems/
```

เพื่อคืนรายการโจทย์ทั้งหมด โดยแสดงแค่ `id` กับ `title` ครับ.

---

## ต่อไปคือ **ขั้นที่ 4: ทำ API จริงตัวแรกของ Step 1** — `GET /api/problems/`

ตอนนี้ `/test-problem` อ่านได้แค่ `P1001.json` แบบเจาะจง แต่ของจริงเราต้องให้มัน **อ่านโจทย์ทุกไฟล์ในโฟลเดอร์ `problems/`** แล้วคืนรายการ `id` กับ `title`

แก้ `main.py` เป็นแบบนี้:

```python
from fastapi import FastAPI
import json
import os

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "OJ server is running"}


@app.get("/test-problem")
async def test_problem():
    with open("problems/P1001.json", "r", encoding="utf-8") as f:
        problem = json.load(f)

    return problem


@app.get("/api/problems/")
async def get_problems():
    problems = []

    for filename in os.listdir("problems"):
        if filename.endswith(".json"):
            path = os.path.join("problems", filename)

            with open(path, "r", encoding="utf-8") as f:
                problem = json.load(f)

            problems.append({
                "id": problem["id"],
                "title": problem["title"]
            })

    return {
        "code": 200,
        "msg": "success",
        "data": problems
    }
```

เซฟ แล้วเปิด:

```text
http://127.0.0.1:8000/api/problems/
```

ตอนนี้มีแค่ `P1001.json` คุณควรเห็นประมาณนี้:

```json
{
    "code": 200,
    "msg": "success",
    "data": [
        {
            "id": "P1001",
            "title": "A+B Problem"
        }
    ]
}
```

สิ่งใหม่มี 3 อย่าง

```python
import os
```

เราใช้ `os` ช่วยจัดการไฟล์และโฟลเดอร์

```python
os.listdir("problems")
```

มันจะดูว่าใน `problems/` มีไฟล์อะไรบ้าง เช่น

```python
["P1001.json"]
```

ถ้ามีสามข้อก็อาจได้:

```python
["P1001.json", "P1002.json", "P1003.json"]
```

แล้ว:

```python
if filename.endswith(".json"):
```

หมายถึงเอาเฉพาะไฟล์ JSON เผื่อในโฟลเดอร์มีไฟล์อื่นปนอยู่

ส่วน:

```python
path = os.path.join("problems", filename)
```

ถ้า:

```python
filename = "P1001.json"
```

มันจะสร้าง path:

```text
problems/P1001.json
```

จากนั้นเราอ่าน JSON เหมือนเดิม แต่แทนที่จะ return ทั้งก้อน เราเลือกแค่:

```python
{
    "id": problem["id"],
    "title": problem["title"]
}
```

เพราะ endpoint นี้เป็น **รายการโจทย์** ไม่ใช่หน้ารายละเอียด

ถ้าอันนี้ทำงาน ขั้นถัดไปเราจะทำ:

```text
GET /api/problems/P1001
```

ให้รับ `problem_id` จาก URL แล้วค้นไฟล์ที่ตรงกับ id นั้นครับ.

---

## ต่อไปทำ **API ตัวที่ 2: ดูรายละเอียดโจทย์ตาม id**

เพิ่มโค้ดนี้ต่อท้าย `main.py`:

```python
@app.get("/api/problems/{problem_id}")
async def get_problem(problem_id: str):
    path = os.path.join("problems", f"{problem_id}.json")

    if not os.path.exists(path):
        return {
            "code": 404,
            "msg": "problem not found",
            "data": None
        }

    with open(path, "r", encoding="utf-8") as f:
        problem = json.load(f)

    return {
        "code": 200,
        "msg": "success",
        "data": problem
    }
```

แล้วเปิด:

```text
http://127.0.0.1:8000/api/problems/P1001
```

ควรได้ข้อมูลเต็มของ `P1001`

จุดสำคัญคือ:

```python
@app.get("/api/problems/{problem_id}")
```

`{problem_id}` หมายถึงค่าที่อยู่ตรง URL จะถูกส่งเข้า parameter นี้

เช่น:

```text
/api/problems/P1001
```

จะทำให้:

```python
problem_id == "P1001"
```

แล้วบรรทัดนี้:

```python
path = os.path.join("problems", f"{problem_id}.json")
```

จะกลายเป็น:

```text
problems/P1001.json
```

ส่วน:

```python
if not os.path.exists(path):
```

เช็กว่าไฟล์มีอยู่จริงไหม

ลองเปิดอันนี้ด้วย:

```text
http://127.0.0.1:8000/api/problems/P9999
```

ตอนนี้ควรเห็น:

```json
{
    "code": 404,
    "msg": "problem not found",
    "data": null
}
```

แต่มีจุดหนึ่งที่เราจะปรับในขั้นถัดไป: ตอนนี้ JSON ข้างในบอก `code: 404` แต่ **HTTP status จริงยังเป็น 200** เพราะเราแค่ `return dict`

ขั้นต่อไปเราจะเรียน `HTTPException` แล้วทำให้ 404 เป็น 404 จริง ๆ ซึ่งเป็นสิ่งที่การบ้านให้ความสำคัญครับ.

---
## ต่อไปทำ **HTTP status code ให้ถูกจริง ๆ** ก่อน เพราะตอนนี้เวลาหา `P9999` ไม่เจอ เราแค่คืน JSON ที่มี `"code": 404` แต่ HTTP response จริงยังเป็น `200 OK` ซึ่งสเปกระบุชัดว่า **ห้ามทุกกรณีตอบ 200** และ `code` ใน JSON ต้องตรงกับ HTTP status จริง ([DBG Course][1])

แก้ import ด้านบนจาก:

```python
from fastapi import FastAPI
```

เป็น:

```python
from fastapi import FastAPI, HTTPException
```

แล้วแก้ `get_problem()` เป็น:

```python
@app.get("/api/problems/{problem_id}")
async def get_problem(problem_id: str):
    path = os.path.join("problems", f"{problem_id}.json")

    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    with open(path, "r", encoding="utf-8") as f:
        problem = json.load(f)

    return {
        "code": 200,
        "msg": "success",
        "data": problem
    }
```

จากนั้นลองเปิด:

```text
http://127.0.0.1:8000/api/problems/P9999
```

คราวนี้ browser จะได้ HTTP `404` จริง

แต่จะมีจุดหนึ่งที่คุณสังเกตได้: FastAPI จะห่อข้อมูลใน `detail` กลายเป็นประมาณ:

```json
{
    "detail": {
        "code": 404,
        "msg": "problem not found",
        "data": null
    }
}
```

ซึ่ง **ยังไม่ตรง response format ของการบ้าน 100%** เพราะสเปกต้องการตรง ๆ:

```json
{
    "code": 404,
    "msg": "problem not found",
    "data": null
}
```

ดังนั้นแทนที่จะใช้ `HTTPException` ตรง ๆ วิธีที่เหมาะกับงานนี้กว่าคือใช้ `JSONResponse`

เพิ่ม import:

```python
from fastapi.responses import JSONResponse
```

แล้วเขียน:

```python
@app.get("/api/problems/{problem_id}")
async def get_problem(problem_id: str):
    path = os.path.join("problems", f"{problem_id}.json")

    if not os.path.exists(path):
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "msg": "problem not found",
                "data": None
            }
        )

    with open(path, "r", encoding="utf-8") as f:
        problem = json.load(f)

    return {
        "code": 200,
        "msg": "success",
        "data": problem
    }
```

อันนี้ตรง specification มากกว่า เพราะทั้งสองอย่างจะเป็น:

```text
HTTP status = 404
JSON code   = 404
```

สเปกกำหนด `404` สำหรับ resource ที่ไม่มี และระบุรูป error response แบบ `{"code":404,"msg":"problem not found","data":null}` โดยตรง ([DBG Course][1])

อีกอย่าง ขอแก้ข้อมูลจากที่ฉันบอกก่อนหน้านี้หนึ่งจุด: **Step 1 เวอร์ชันปัจจุบันมี Edit Problem ด้วย** คือ

```text
PUT /api/problems/{problem_id}
```

ดังนั้น Step 1 จริง ๆ มี 5 operations:

```text
GET    /api/problems/              รายการโจทย์
GET    /api/problems/{id}          รายละเอียดโจทย์
POST   /api/problems/              เพิ่มโจทย์
PUT    /api/problems/{id}          แก้โจทย์
DELETE /api/problems/{id}          ลบโจทย์
```

เอกสาร Step 1 ระบุว่าต้องรองรับ “增删改查” และ API docs กำหนด `PUT` ไว้โดยเฉพาะ ([DBG Course][2])

ทำ `JSONResponse` ให้ `P9999` ได้ 404 ก่อน แล้ว **ขั้นต่อไปเราจะทำ `POST /api/problems/`** ซึ่งจะเป็นครั้งแรกที่เราใช้ Pydantic รับ JSON จากผู้ใช้และตรวจ field อัตโนมัติครับ.

---

## เราสามารถมีฟังก์ชันชื่อเดียวกันในไฟล์เดียวกันได้ไหม

ได้แน่นอนครับ 😂 **Python 1 ไฟล์มีฟังก์ชันกี่ฟังก์ชันก็ได้** ไม่ได้จำกัดว่าหนึ่งไฟล์ต้องมีฟังก์ชันเดียว

เช่น:

```python
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b
```

ทั้งหมดอยู่ใน `main.py` ไฟล์เดียวกันได้

กรณี FastAPI ของเราเหมือนกัน:

```python
@app.get("/")
async def root():
    return {"message": "OJ server is running"}


@app.get("/api/problems/")
async def get_problems():
    ...


@app.get("/api/problems/{problem_id}")
async def get_problem(problem_id: str):
    ...
```

นี่คือ **3 ฟังก์ชันในไฟล์เดียว**

แต่สิ่งที่ FastAPI เพิ่มเข้ามาคือ decorator เช่น:

```python
@app.get("/api/problems/")
```

มันบอก FastAPI ว่า:

> ถ้ามีคนส่ง `GET` มาที่ `/api/problems/` ให้เรียกฟังก์ชัน `get_problems()`

ส่วน:

```python
@app.get("/api/problems/{problem_id}")
```

บอกว่า:

> ถ้ามีคน GET เช่น `/api/problems/P1001` ให้เรียก `get_problem()` และเอา `"P1001"` ใส่ `problem_id`

ดังนั้นมันเหมือนเรามีหลายฟังก์ชันธรรมดา:

```text
main.py

root()
get_problems()
get_problem()
```

แต่ FastAPI สร้าง **เส้นทาง (route)** เชื่อม URL เข้ากับแต่ละฟังก์ชัน:

```text
GET /
        ─────────→ root()

GET /api/problems/
        ─────────→ get_problems()

GET /api/problems/P1001
        ─────────→ get_problem("P1001")

GET /api/problems/P1234
        ─────────→ get_problem("P1234")
```

และจริง ๆ โปรเจกต์ใหญ่ ๆ จะมี **หลายสิบหรือหลายร้อยฟังก์ชัน** เพียงแต่พอโปรเจกต์ใหญ่ขึ้น เราจะไม่ยัดทุกอย่างไว้ `main.py` แต่จะแยกเป็นหลายไฟล์ เช่น `problems.py`, `users.py`, `judge.py`

ตอนนี้งานเรายังเล็ก การรวมไว้ใน `main.py` ก่อนจะช่วยให้คุณเข้าใจ FastAPI ง่ายกว่าครับ.
