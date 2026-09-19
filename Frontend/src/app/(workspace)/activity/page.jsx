'use client';

import { Activity } from 'lucide-react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel } from '@/components/page-ui';

export default function ActivityPage() {
  const { data } = useWorkspace();
  const records = data.audit || [];
  return <><PageIntro eyebrow="AUDIT TRAIL" title="Activity" description="See who changed each important record and when the change happened." /><Panel eyebrow="LATEST EVENTS" title="Workspace activity" meta={`${records.length} events`}>{records.length ? <div className="timeline">{records.map((item) => <article key={item.id}><i /><div><strong>{item.action}</strong><p>{item.user_name || 'System'} · {item.entity} {item.entity_id ? `#${item.entity_id}` : ''}</p><small>{item.created_at}{item.detail ? ` · ${item.detail}` : ''}</small></div></article>)}</div> : <Empty icon={Activity} title="No activity yet" text="Saved actions will appear here automatically." />}</Panel></>;
}
