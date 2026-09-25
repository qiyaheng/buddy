import { CheckCircleFilled, CloseCircleFilled, LoadingOutlined } from '@ant-design/icons'
import type { PlanBlock as PlanBlockType, PlanStepStatus } from '../../../types/chat'

function StepIcon({ status }: { status: PlanStepStatus }) {
  if (status === 'done') return <CheckCircleFilled className="plan-ic plan-ic-done" />
  if (status === 'running') return <LoadingOutlined className="plan-ic plan-ic-running" />
  if (status === 'error') return <CloseCircleFilled className="plan-ic plan-ic-error" />
  return <span className="plan-ic plan-ic-pending" />
}

export default function PlanBlock({ block }: { block: PlanBlockType }) {
  return (
    <div className="block-plan">
      <div className="block-plan-title">执行计划</div>
      <div className="plan-steps">
        {block.steps.map((step, i) => (
          <div className={`plan-step plan-step-${step.status}`} key={step.id}>
            <span className="plan-step-rail">
              <StepIcon status={step.status} />
              {i < block.steps.length - 1 && <span className="plan-step-line" />}
            </span>
            <span className="plan-step-label">
              {step.title}
              {step.status === 'running' && <span className="plan-step-hint">执行中…</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
