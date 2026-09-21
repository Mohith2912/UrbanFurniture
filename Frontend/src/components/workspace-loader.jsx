import Image from 'next/image';

export default function WorkspaceLoader({ compact = false, message = 'Preparing your workspace' }) {
  return <main className={`workspace-loader ${compact ? 'is-compact' : ''}`} aria-live="polite" aria-busy="true">
    <div className="loader-scene" aria-hidden="true">
      <span className="loader-halo" />
      <span className="loader-orbit"><i /><i /><i /></span>
      <span className="loader-tile tile-one" /><span className="loader-tile tile-two" /><span className="loader-tile tile-three" /><span className="loader-tile tile-four" />
      <span className="loader-logo"><Image src="/urban-furniture-logo.png" alt="" width={58} height={58} priority /></span>
    </div>
    <div className="loader-copy"><small>URBAN FURNITURE</small><strong>{message}</strong><p>Connecting live records and arranging your view</p></div>
    <div className="loader-progress" aria-hidden="true"><i /></div>
  </main>;
}
