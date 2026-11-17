from datetime import datetime, date
from typing import Optional, Literal
from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    login: str
    password: str

class RegisterRequestIn(BaseModel):
    login: str = Field(min_length=3, max_length=100)
    email: Optional[str] = None
    department_id: int
    message: Optional[str] = None

class ResetRequestIn(BaseModel):
    login: str

class ResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=6)

class DepartmentOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class DepartmentIn(BaseModel):
    name: str
    code: Optional[str] = None

class UserOut(BaseModel):
    id: int
    login: str
    email: Optional[str]
    department_id: int
    department_name: Optional[str] = None
    role: str
    is_active: bool
    class Config:
        from_attributes = True

class ApproveIn(BaseModel):
    login: str
    password: str = Field(min_length=6)
    role: Literal["user", "admin"] = "user"

class ChangeDeptIn(BaseModel):
    department_id: int

class DeloIn(BaseModel):
    base_title: str
    year: int
    retention: Optional[str] = None

class DeloOut(BaseModel):
    id: int
    department_id: int
    department_name: Optional[str] = None
    index_code: str
    base_title: str
    year: int
    retention: Optional[str]
    status: str
    full_title: str
    class Config:
        from_attributes = True

class TomOut(BaseModel):
    id: int
    delo_id: int
    tom_number: int
    max_pages: int
    status: str
    current_end: int = 0
    class Config:
        from_attributes = True

class DraftItemIn(BaseModel):
    source: Literal["external", "manual"]
    external_ref: Optional[str] = None
    title: Optional[str] = None
    account_number: Optional[str] = None
    page_count: Optional[int] = None
    type_id: Optional[int] = None
    
    # Дополнительные поля
    incoming_num: Optional[str] = None
    incoming_date: Optional[date] = None
    outgoing_num: Optional[str] = None
    outgoing_date: Optional[date] = None
    copy_num: Optional[str] = None
    cipher: Optional[str] = None
    grif: Optional[str] = None
    organ: Optional[str] = None
    doc_num: Optional[str] = None
    employee: Optional[str] = None

class DraftItemsPayload(BaseModel):
    items: list[DraftItemIn]

class DraftItemPatch(BaseModel):
    title: Optional[str] = None
    account_number: Optional[str] = None
    page_count: Optional[int] = Field(default=None, gt=0, le=250)
    position: Optional[int] = None
    
    # Дополнительные поля для редактирования
    doc_num: Optional[str] = None
    organ: Optional[str] = None
    cipher: Optional[str] = None
    incoming_num: Optional[str] = None
    incoming_date: Optional[date] = None
    outgoing_num: Optional[str] = None
    outgoing_date: Optional[date] = None
    copy_num: Optional[str] = None
    grif: Optional[str] = None
    employee: Optional[str] = None

class ReorderIn(BaseModel):
    order: list[int]

class ExternalDocOut(BaseModel):
    external_ref: str
    title: str
    account_number: Optional[str]
    page_count: int
    placed: Optional[dict] = None
    class Config:
        from_attributes = True
