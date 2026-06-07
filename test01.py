from fastapi import FastAPI

app = FastAPI()

# GET请求：查询数据
@app.get("/items")
def get_items():
    return {"items": ["item1", "item2", "item3"]}

# POST请求：新增数据
@app.post("/items")
def create_item():
    return {"message": "创建商品成功"}

# PUT请求：修改数据
@app.put("/items/1")
def update_item():
    return {"message": "修改商品1成功"}

# DELETE请求：删除数据
@app.delete("/items/1")
def delete_item():
    return {"message": "删除商品1成功"}

# PATCH请求：部分修改数据
@app.patch("/items/1")
def patch_item():
    return {"message": "部分修改商品1成功"}

# 正确：具体路由在前
@app.get("/users/me")
def read_user_me():
    return {"user_id": "当前用户"}

@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}

# 错误：通用路由在前会匹配所有请求
# @app.get("/users/{user_id}")
# def read_user(user_id: int):
#     return {"user_id": user_id}

# @app.get("/users/me")
# def read_user_me():
#     return {"user_id": "当前用户"}