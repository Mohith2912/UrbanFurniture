'use client';

import { Boxes } from 'lucide-react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel, Status } from '@/components/page-ui';
import { money } from '@/lib/format';

export default function InventoryPage() {
  const { data } = useWorkspace();
  const stock = data.stock || [];
  return <><PageIntro eyebrow="STOCK CONTROL" title="Inventory" description="See current quantities, reorder levels and the indicative value of furniture held for sale." /><section className="next-metrics"><article><span>Stock items</span><strong>{stock.length}</strong><small>Goods and combos</small></article><article className="featured"><span>Indicative value</span><strong>{money(stock.reduce((sum, item) => sum + Number(item.cost || 0) * Number(item.quantity || 0), 0), 0)}</strong><small>Quantity at current cost</small></article><article><span>Low stock</span><strong>{stock.filter((item) => Number(item.quantity) <= Number(item.reorder_level || 0)).length}</strong><small>At or below reorder level</small></article><article><span>Stock source</span><strong>Posted</strong><small>Bills receive and invoices issue</small></article></section><Panel eyebrow="LIVE STOCK" title="Inventory register" meta={`${stock.length} items`}>{stock.length ? <div className="section-table">{stock.map((item) => <div className="section-row" key={item.id}><span><b>{item.name}</b><small>{item.category || 'Uncategorized'}</small></span><span><strong>{Number(item.quantity).toLocaleString('en-IN')} units</strong><small>{money(item.cost)} current cost</small></span><Status tone={Number(item.quantity) <= Number(item.reorder_level || 0) ? 'amber' : 'green'}>{Number(item.quantity) <= Number(item.reorder_level || 0) ? 'Reorder' : 'In stock'}</Status></div>)}</div> : <Empty icon={Boxes} title="No stock items" text="Add products and post a vendor bill to receive stock." />}</Panel></>;
}
