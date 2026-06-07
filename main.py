from fastapi import FastAPI
import uvicorn

# 第一个FastAPI应用
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# 第二个FastAPI应用
testapp = FastAPI()


# GET请求：查询数据
@testapp.get("/items")
def get_items():
    return {"items": ["item1", "item2", "item3"]}

# POST请求：新增数据
@testapp.post("/items")
def create_item():
    return {"message": "创建商品成功"}

# PUT请求：修改数据
@testapp.put("/items/1")
def update_item():
    return {"message": "修改商品1成功"}

# DELETE请求：删除数据
@testapp.delete("/items/1")
def delete_item():
    return {"message": "删除商品1成功"}

# PATCH请求：部分修改数据
@testapp.patch("/items/1")
def patch_item():
    return {"message": "部分修改商品1成功"}

if __name__ == "__main__":
    # uvicorn.run(app="main:app", host="127.0.0.1", port=8000)
    uvicorn.run(app="main:testapp", host="127.0.0.1", port=8000)

# from fastapi import FastAPI
# import uvicorn
 
# # 1. 创建应用实例
# app = FastAPI()
 
# # 2. 定义路由
# @app.get("/")
# def root():
#     return {"message": "Hello World"}
 
# # 3. 启动入口（也可以在命令行运行）
# if __name__ == "__main__":
#     uvicorn.run(app="main:app", host="127.0.0.1", port=8000)

'''
这里的 "main:app" 意思是：运行 main.py 文件里的 app 对象

启动服务的方式有2个：

第一个是在代码上面写入if __name__ == "__main__":
    uvicorn.run(app="main:app", host="127.0.0.1", port=8000)语句直接运行启动
————————————————

第二个是在命令行/终端运行：
uvicorn main:app --host 127.0.0.1 --port 8000

'''