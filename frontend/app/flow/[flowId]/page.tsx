import { notFound } from 'next/navigation'
import { FlowWizard } from '@/components/FlowWizard'
import type { FlowId } from '@/lib/types'
import { FLOW_CONFIGS } from '@/lib/flowConfigs'

const IDS = new Set(Object.keys(FLOW_CONFIGS))

export default function FlowPage({ params }: { params: { flowId: string } }) {
  if (!IDS.has(params.flowId)) notFound()
  return <FlowWizard flowId={params.flowId as FlowId} />
}
