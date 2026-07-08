from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
import json

app = FastAPI()

class Patient(BaseModel):
    id: Annotated[str, Field( description="The ID of the patient" , example = "P001")]
    name: Annotated[str, Field( description="The name of the patient" , example = "John Doe")]
    age: Annotated[int, Field( gt = 0 , le = 120 , description="The age of the patient" , example = 30)]
    gender: Annotated[Literal['male','female','other'] , Field(..., description="The gender of the patient" , example = "male")]
    weight: Annotated[float, Field( gt = 0 , description="The weight of the patient in kg" )]
    height: Annotated[float, Field( gt = 0 , description="The height of the patient in m" )]
    
    @computed_field
    @property
    def bmi(self)-> float:
        return round(self.weight/self.height**2 , 2)
    
    @computed_field
    @property
    def verdict(self)->str:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal weight"
        elif self.bmi < 30:
            return "Overweight"
        else:
            return "Obese"
        
    """Even though the verdict is a computed field, it is still included in the schema and can be used in the response model.
       This is because as soon as the second computed field is trigered , the first computed field is also triggered and included 
       in the response model.
    """

class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0)]
    gender: Annotated[Optional[Literal['male', 'female']], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]


def load_data():
    with open("patients.json",'r') as f:
        return json.load(f)
    

def save_data(data):
    with open("patients.json" , 'w') as f:
        json.dump(data , f , indent = 4)
    

@app.get('/')
def home():
    return {"message" : "Welcome to the Patient Records API"}


@app.get('/about')
def about():
    return {'message': 'A fully functional API to manage your patient records'}


@app.get('/view')
def view():
    data = load_data()
    return data


@app.get('/patient/{patient_id}')
def view_patient(patient_id: str = Path(..., description='ID of the patient in the DB', example='P001')):
    data = load_data()

    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail='Patient not found')


@app.get('/sort')
def sort_patients(sort_by: str = Query(..., description='Sort on the basis of height, weight or bmi'), order: str = Query('asc', description='sort in asc or desc order')):
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f'Invalid field select from {valid_fields}')
    
    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail='Invalid order select between asc and desc')
    
    data = load_data()
    sort_order = True if order=='desc' else False
    sorted_data = sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse=sort_order)
    return sorted_data


@app.post('/create')
def append_patient(patient: Patient):
    data = load_data()
    if patient.id in data:
        raise HTTPException(status_code=400, detail='Patient with this ID already exists')
    
    data[patient.id] = patient.model_dump(exclude = ['id'])
    save_data(data)
    return JSONResponse( status_code = 201 , content = {'message' : 'Patient record created successfully'})
    
 
@app.put('/edit/{patient_id}')
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail='Patient not found')
    
    existing_patient_info = data[patient_id]
    updated_patient_info = patient_update.model_dump(exclude_unset=True) # this is done to avoid including those values whose value was not provided in the request body. If we don't do this, then the values of those fields will be set to None and will be lost.

    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    #existing_patient_info -> pydantic object -> updated bmi + verdict
    existing_patient_info['id'] = patient_id # This is done to ensure that the id is included in the pydantic object, as it is a required field in the Patient model. If we don't do this, then the id will be missing from the pydantic object and will cause an error when we try to create a new Patient object.
    patient_pydandic_obj = Patient(**existing_patient_info)
    #-> pydantic object -> dict
    existing_patient_info = patient_pydandic_obj.model_dump(exclude='id') # Excluding the ID as it is not part of HTTP requiest body and the ID is already provided in the path parameter.

    data[patient_id] = existing_patient_info
    save_data(data)
    return JSONResponse(status_code=200, content={'message':'patient updated'})

@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(status_code=404, detail='Patient not found')
    
    del data[patient_id]
    save_data(data)
    return JSONResponse(status_code=200, content={'message':'patient deleted'})