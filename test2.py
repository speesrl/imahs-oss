import json 


from dataclasses import dataclass



@dataclass
class FileUpload:
    filename: str
    file: str 
    content_type: str
    @staticmethod
    def __json__(o):
        return vars(o)


print(
    json.dumps({'f': FileUpload('1', '2', '3')}, default=FileUpload.__json__)
)