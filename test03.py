from fastapi import FastAPI
import uvicorn
app = FastAPI()
 
@app.get("/student/{student_id}")  # 注意花括号 {}
def get_student(student_id: int):  # 注意这里写了 : int
    return {
        "学生ID": student_id,
        "类型": str(type(student_id))
    }
 
if __name__=="__main__":
    uvicorn.run(app="test03:app",host="127.0.0.1",port=8088)