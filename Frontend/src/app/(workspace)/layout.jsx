import AppShell from '@/components/app-shell';
import { WorkspaceProvider } from '@/components/workspace-provider';

export default function WorkspaceLayout({ children }) { return <WorkspaceProvider><AppShell>{children}</AppShell></WorkspaceProvider>; }
