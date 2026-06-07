from fastapi import FastAPI

app = FastAPI(
    title="我的API文档",
    description="这是一个用FastAPI编写的API文档",
    version="1.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API支持团队",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/my_docs",  # 自定义Swagger UI路径
    redoc_url="/my_redoc",  # 自定义ReDoc路径
    openapi_url="/openapi.json"  # 自定义OpenAPI规范路径
)