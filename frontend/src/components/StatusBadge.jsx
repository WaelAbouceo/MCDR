export function StatusBadge({ status }) {
  const cls = `badge badge-${status}`;
  return <span className={cls}>{status?.replace(/_/g, ' ')}</span>;
}

export function PriorityBadge({ priority }) {
  const cls = `badge badge-${priority}`;
  return <span className={cls}>{priority}</span>;
}
