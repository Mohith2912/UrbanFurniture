import Image from 'next/image';

export default function Brand({ compact = false, inverse = false }) {
  return <div className={`brand-lockup ${compact ? 'is-compact' : ''} ${inverse ? 'is-inverse' : ''}`}>
    <span className="brand-symbol"><Image src="/urban-furniture-logo.png" alt="" width={48} height={48} priority /></span>
    <span className="brand-copy"><strong>Urban Furniture</strong><small>Books & Business</small></span>
  </div>;
}
