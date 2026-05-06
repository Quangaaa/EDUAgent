from pydantic import BaseModel, Field
from typing import Literal

class AuthPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)

class SessionCreatePayload(BaseModel):
    title: str = Field(default="New Session", min_length=1, max_length=100) #新会话创建

class AskPayload(BaseModel):
    query: str = Field(min_length=1, max_length=5000) # 问题字数控制在1-5000之间
    mode: Literal["chat", "agent", "plan"] = Field(default="chat")