"""FastAPI service. Run from /backend:  uvicorn app.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .experiments import adjust_pvalues, compare_proportions, srm_check
from .power import sample_size_means, sample_size_proportions

app = FastAPI(title="Experimentation Platform", version="0.1.0")


class ProportionPower(BaseModel):
    p_baseline: float = Field(..., gt=0, lt=1, examples=[0.10])
    mde_abs: float = Field(..., examples=[0.01])
    alpha: float = Field(0.05, gt=0, lt=1)
    power: float = Field(0.8, gt=0, lt=1)


class MeanPower(BaseModel):
    sd: float = Field(..., gt=0)
    mde_abs: float
    alpha: float = Field(0.05, gt=0, lt=1)
    power: float = Field(0.8, gt=0, lt=1)


class SRMInput(BaseModel):
    n_control: int = Field(..., gt=0)
    n_treatment: int = Field(..., gt=0)
    expected_treat_share: float = Field(0.5, gt=0, lt=1)


class ProportionsInput(BaseModel):
    conv_control: int = Field(..., ge=0)
    n_control: int = Field(..., gt=0)
    conv_treatment: int = Field(..., ge=0)
    n_treatment: int = Field(..., gt=0)
    alpha: float = Field(0.05, gt=0, lt=1)


class AdjustInput(BaseModel):
    p_values: list[float] = Field(..., min_length=1)
    method: str = "benjamini-hochberg"
    alpha: float = Field(0.05, gt=0, lt=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/power/proportions")
def power_proportions(body: ProportionPower):
    try:
        return sample_size_proportions(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/power/means")
def power_means(body: MeanPower):
    try:
        return sample_size_means(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/doctor/srm")
def doctor_srm(body: SRMInput):
    return srm_check(**body.model_dump())


@app.post("/experiments/proportions")
def experiments_proportions(body: ProportionsInput):
    try:
        return compare_proportions(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/experiments/adjust-pvalues")
def experiments_adjust(body: AdjustInput):
    try:
        return adjust_pvalues(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
