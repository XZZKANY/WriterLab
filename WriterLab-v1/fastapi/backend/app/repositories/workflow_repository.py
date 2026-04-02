from sqlalchemy.orm import Session

from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep


def get_workflow_run(db: Session, workflow_id):
    return db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()


def list_workflow_steps(db: Session, workflow_id):
    return (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_run_id == workflow_id)
        .order_by(WorkflowStep.step_order.asc(), WorkflowStep.attempt_no.asc())
        .all()
    )
