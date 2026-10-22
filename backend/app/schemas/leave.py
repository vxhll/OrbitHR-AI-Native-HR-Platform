from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(min_length=1, max_length=30)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        return self


class LeaveDecisionRequest(BaseModel):
    approval_status: str

    @model_validator(mode="after")
    def validate_status(self):
        if self.approval_status not in {"Approved", "Rejected"}:
            raise ValueError("Decision must be Approved or Rejected")
        return self


class LeaveRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    days: int
    approval_status: str
    approved_by: str | None
