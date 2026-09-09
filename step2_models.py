from pydantic import BaseModel # a library that FastAPI uses to manage and validate data

# class Student:
#     def __init__(self, name, age):
#         self.name = name
#         self.age = age
# student = Student("Student", 22)
# student
# ├── name = "Student"
# └── age = 22
# 
# class Student(BaseModel):
#     name: str
#     age: int
# student = Student(
#     name="Student",
#     age=22
# )
#
# It also checks the type:
# Student(
#     name="Student",
#     age="hello"
# )
# It will show an error because we defined:
#     age: int
# but "hello" is not an integer, this is called data validation


class Submission(BaseModel):
    problem_id: str
    language: str
    code: str

# JSON
# {
#     "problem_id": "P1001",
#     "language": "cpp",
#     "code": "..."
# }
# will create
# Submission(
#     problem_id="P1001",
#     language="cpp",
#     code="..."
# )


class LanguageConfig(BaseModel):
    name: str
    file_ext: str
    compile_cmd: str | None = None 
    # str -> compile_cmd = "g++ {src} -o {exe}" 
    # None -> compile_cmd = None -> Because some languages ​​require compilation, while others do not.
    # = None -> If no value is specified, use None as the default
    run_cmd: str

    time_limit: float | None = None
    memory_limit: int | None = None