"""FastAPI service. Run from /backend:  uvicorn app.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .experiments import adjust_pvalues, compare_proportions, srm_check
from .power import sample_size_means, sample_size_proportions

from .sequential import compare_strategies, sequential_check

from typing import Literal

from .bayesian import bayesian_ab_analytic, bayesian_ab_pymc

from .causal import compare_methods

from .causal import compare_methods, compare_panel_methods

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from .analyze import analyze_ab, load_csv, preview

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

class SequentialCheckInput(BaseModel):
    mean_diff: float
    n_per_group: int = Field(..., gt=0)
    sd: float = Field(..., gt=0)
    tau: float | None = Field(None, gt=0)
    alpha: float = Field(0.05, gt=0, lt=1)


class PeekingDemoInput(BaseModel):
    true_effect: float = 0.0
    n_looks: int = Field(10, ge=2, le=30)
    users_per_look: int = Field(500, gt=0, le=100_000)
    n_sims: int = Field(5_000, ge=100, le=50_000)
    alpha: float = Field(0.05, gt=0, lt=1)

class BayesianInput(BaseModel):
    conv_a: int = Field(..., ge=0)
    n_a: int = Field(..., gt=0)
    conv_b: int = Field(..., ge=0)
    n_b: int = Field(..., gt=0)
    prior_alpha: float = Field(1.0, gt=0)
    prior_beta: float = Field(1.0, gt=0)
    engine: Literal["analytic", "pymc"] = "analytic"

class CausalCompareInput(BaseModel):
    n: int = Field(5_000, ge=500, le=20_000)
    true_effect: float = 2.0
    confounding: float = Field(1.0, ge=0, le=5)
    hidden_confounding: float = Field(0.0, ge=0, le=3)
    seed: int = 0
    use_dowhy: bool = False      # slower (a few seconds)
    use_econml: bool = False     # slower (about 10 seconds)

class PanelCompareInput(BaseModel):
    true_effect: float = -3.0
    loading_spread: float = Field(1.0, ge=0, le=2)   # 0 = parallel trends holds
    n_donors: int = Field(30, ge=5, le=60)
    n_treated: int = Field(1, ge=1, le=10)
    n_pre: int = Field(20, ge=6, le=40)
    n_post: int = Field(10, ge=3, le=20)
    seed: int = 0


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

@app.post("/sequential/check")
def sequential_check_endpoint(body: SequentialCheckInput):
    try:
        return sequential_check(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/sequential/peeking-demo")
def peeking_demo(body: PeekingDemoInput):
    return compare_strategies(**body.model_dump())

@app.post("/bayesian/ab")
def bayesian_ab(body: BayesianInput):
    args = body.model_dump()
    engine = args.pop("engine")
    try:
        if engine == "pymc":
            return bayesian_ab_pymc(**args)
        return bayesian_ab_analytic(**args)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.post("/causal/compare")
def causal_compare(body: CausalCompareInput):
    return compare_methods(**body.model_dump())

@app.post("/causal/panel-compare")
def causal_panel_compare(body: PanelCompareInput):
    return compare_panel_methods(**body.model_dump())

# ---------------------------------------------------------------- upload + analyze
MAX_UPLOAD_BYTES = 50 * 1024 * 1024   # 50 MB; sample very large datasets first


async def _read_upload(file: UploadFile):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is over 50 MB. Please upload a sample of the rows.")
    try:
        return load_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/analyze/preview")
async def analyze_preview(file: UploadFile = File(...)):
    """Upload a CSV and get its columns back, so a UI can offer sensible choices."""
    return preview(await _read_upload(file))


@app.post("/analyze/ab")
async def analyze_ab_endpoint(
    file: UploadFile = File(...),
    group_col: str = Form(...),
    metric_col: str = Form(...),
    control_label: str | None = Form(None),
    treatment_label: str | None = Form(None),
    metric_type: str = Form("auto"),
    pre_metric_col: str | None = Form(None),
    expected_treat_share: float = Form(0.5),
    alpha: float = Form(0.05),
):
    """Upload an A/B test CSV; get Experiment Doctor checks, results and a plain-English verdict."""
    df = await _read_upload(file)
    try:
        return analyze_ab(df, group_col, metric_col, control_label or None, treatment_label or None,
                          metric_type, pre_metric_col or None, expected_treat_share, alpha)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))